# V3.3.7 – Local Checkpoint / Resume

First run: `python refresh_silver_ai.py --max-symbols 0 --exchanges HOSE,HNX,UPCOM --enrich-growth --checkpoint-every 20`

After interruption on **the same calendar day**, run the same command with `--resume`.

Checkpoint stored locally in `.refresh_checkpoint/` and excluded from Git. Previous V3.3.6 interrupted work is unrecoverable. A changed date window or changed symbol list causes checkpoint mismatch; `--reset-checkpoint` starts fresh. Unsuccessful attempts are skipped on resume; a fresh run retries them. Sector mapping still needs verified data. Keep existing `data_cache` backup.
