# Task Generation Prompt

You are an expert technical writer and release manager. Your task is to generate or update a `TASKS.md` file based on a list steps needed to complete phases for tracking purposes.  You will follow the example below and apply it to our podb project. 


## P0

- [ ] Fix authentication crash on token refresh
  - **ID**: auth-fix
  - **Tags**: backend, auth
  - **Details**: JWT refresh returns 500 on expired tokens
  - **Files**: `src/auth/refresh.ts`, `src/middleware/auth.ts`
  - **Acceptance**: Refresh works, tests pass, regression test added

## P1

- [ ] Add rate limiting to public API endpoints (@cursor-1)
  - **Tags**: backend
  - **Estimate**: 1h
  - **Details**: Use express-rate-limit, 100 req/min per IP
  - **Hypothesis**: Capping public endpoints at 100 req/min/IP drops the
    abusive-traffic 5xx rate from ~3% to <0.5% without affecting legitimate
    users (steady-state p95 latency unchanged).
  - **Success**: 5xx rate <0.5% over a 24h window post-deploy; p95 latency delta within ±10ms.
  - **Pivot**: if legitimate clients trip the limiter at >1% rate, the per-IP
    model is wrong — switch to per-API-key buckets instead of widening the cap.
  - **Measurement**:
    `curl -s https://api.example.com/metrics | grep http_5xx_rate_24h`
  - **Anchor**: Beyer et al., *SRE* 2016, Ch. 5 (eliminating toil with rate limits).
  - **Verification**: `vitest run tests/rate-limit.test.ts` exits 0; staging soak ≥1h with no false-positives.
  - **Risk**: shared NAT egress (corp networks) could trip the limit. Mitigation: `X-Forwarded-For` honored when behind trusted proxy.
  - **Blocked by**: auth-fix

## P2

- [ ] Update README with new API endpoints

## P3

- [ ] Support WebSocket connections
