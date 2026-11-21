# Supabase private development branch

See [cloud setup and test status](deploy/README.md) for the current branch configuration.

# AI Career Coach · DeepSeek local integration

This development branch runs on http://127.0.0.1:8111/. GitHub Pages continues to serve the archived offline demo.

Set `DEEPSEEK_API_KEY` in your local shell, in `backend/.env`, or in the private shared file `~/.config/ai-career-coach/deepseek.env`. Restart the backend after editing credentials. The backend uses `deepseek-flash` with thinking disabled. Each request allows up to 64,000 input characters and defaults to 3,072 output tokens. A workflow may include several calls for extraction and evidence checks. An insufficient-balance response blocks further requests until restart.

Install Node 22 and Python 3.11+, then run:

```sh
./start.sh
```
