# 배포 가이드 (k3s + ArgoCD)

서울 아파트 분석 플랫폼의 빌드·배포 흐름. **GitOps**라 클러스터를 직접 만지지 않고,
이미지를 푸시한 뒤 매니페스트 git을 커밋하면 **ArgoCD가 자동 동기화**한다.

## 구성 한눈에

| 항목 | 값 |
|------|-----|
| 클러스터 | k3s (단일 노드) |
| 배포 도구 | ArgoCD (auto-sync: `prune=true`, `selfHeal=true`) |
| 매니페스트 repo | `/home/ubuntu/server/k8s-manifests` (`master`), ArgoCD가 `file:///local-manifests` 로 마운트 |
| 매니페스트 경로 | `apps/seoul-apt/` (`app.yaml`, `namespace.yaml`) |
| 레지스트리 | `localhost:30500` (클러스터 내 registry 네임스페이스) |
| 이미지 | `localhost:30500/seoul-apt:<tag>` (베이스: `seoul-apt-base:<tag>`) |
| 서비스 | NodePort **31002** → 컨테이너 8009 |
| DB | SQLite, PVC `seoul-apt-db-pvc`(2Gi)로 영속. 배포해도 데이터 유지 |
| 배포 전략 | `Recreate` (RWO PVC라 롤링 불가 — 구 파드 종료 후 신 파드) |

## 이미지 두 단계(베이스/앱)

무거운 의존성을 **베이스 이미지**에 고정해, 코드만 바뀔 때의 빌드를 수 초로 줄인다.

- **베이스** `Dockerfile.base` → `seoul-apt-base` : python3.12-slim + ca-certificates +
  node22 + `@anthropic-ai/claude-code` + pip 의존성(`requirements.txt`). 느림(~1분+).
- **앱** `Dockerfile` → `seoul-apt` : `FROM seoul-apt-base` + `COPY app/` + entrypoint. 빠름.

**언제 베이스를 다시 빌드하나?**
- `app/requirements.txt` 가 바뀌었을 때
- claude CLI 버전(`CLAUDE_CLI_VERSION`)을 올릴 때
- 베이스가 레지스트리에 없을 때(자동 감지·강제 빌드)

그 외(앱 코드만 변경)에는 베이스를 건드리지 않는다.

## 빌드

```bash
# 앱만 빌드·푸시(베이스 재사용) — 일상 배포
./scripts/build.sh v3

# requirements.txt 를 손댔다면 베이스도 같이 재빌드
./scripts/build.sh v3 --base
```

`scripts/build.sh` 가 베이스 존재 여부를 확인하고, 없거나 `--base` 면 베이스를 먼저
빌드·푸시한 뒤 앱 이미지를 `FROM 베이스`로 빌드·푸시한다.

> 태그는 **올려가며**(v2 → v3 …) 쓴다. 같은 태그를 덮으면 ArgoCD가 매니페스트 변화를
> 못 느껴 롤아웃이 안 일어난다(아래 참고).

## 배포 (ArgoCD)

이미지를 푸시했으면 매니페스트의 태그를 바꿔 커밋한다.

```bash
# 1) app.yaml 의 image 태그 변경
cd /home/ubuntu/server/k8s-manifests
sed -i 's#seoul-apt:v2#seoul-apt:v3#' apps/seoul-apt/app.yaml   # 또는 직접 편집

# 2) 커밋 (ArgoCD는 이 repo의 HEAD를 본다)
git add apps/seoul-apt/app.yaml
git commit -m "seoul-apt v3 배포"

# 3) (선택) 즉시 반영 — auto-sync라 안 해도 수 분 내 자동. 강제하려면:
kubectl -n argocd annotate applications.argoproj.io seoul-apt argocd.argoproj.io/refresh=hard --overwrite
```

auto-sync가 켜져 있어 커밋만 하면 ArgoCD가 새 커밋을 감지해 알아서 롤아웃한다.

## claude 자격증명 Secret (AI 코멘트)

AI 코멘트(`AI_PROVIDER=cli`)는 컨테이너 안에서 `claude -p`를 실행한다. 자격증명은 git에
넣지 않고 **Secret으로 클러스터에만** 둔다(매니페스트에는 마운트만 선언).

```bash
# 호스트의 ~/.claude/.credentials.json 으로 Secret 생성/갱신
kubectl -n seoul-apt create secret generic claude \
  --from-file=.credentials.json=$HOME/.claude/.credentials.json \
  --dry-run=client -o yaml | kubectl apply -f -
```

- Deployment가 이 Secret을 `/secrets/claude`(read-only)로 마운트하고,
  `entrypoint.sh`가 쓰기 가능한 `$HOME/.claude`로 복사한다(claude CLI가 토큰을 갱신하며
  파일에 되쓰기 때문에 read-only 직접 사용 불가).
- Secret이 없으면 AI 코멘트만 graceful-fail하고 나머지 기능은 정상.
- 이 Secret은 git에 없으므로 ArgoCD의 prune 대상이 아니다(수동 관리). 토큰이 만료되면
  위 명령으로 갱신 후 파드 재시작: `kubectl -n seoul-apt rollout restart deploy/seoul-apt`

## 검증

```bash
kubectl -n seoul-apt get pods -l app=seoul-apt        # 1/1 Running
kubectl -n seoul-apt logs deploy/seoul-apt | head      # ▶ claude 자격증명 셋업 완료 / migrate / runserver
kubectl -n argocd get applications.argoproj.io seoul-apt   # Synced / Healthy
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:31002/   # 200
```

## 롤백

매니페스트의 이미지 태그를 이전 값으로 되돌려 커밋하면 끝(이전 이미지가 레지스트리에 남아 있어야 함).

```bash
cd /home/ubuntu/server/k8s-manifests
# app.yaml 의 image 를 직전 태그(예: v2)로 되돌리고
git commit -am "seoul-apt 롤백 → v2" && \
kubectl -n argocd annotate applications.argoproj.io seoul-apt argocd.argoproj.io/refresh=hard --overwrite
```
