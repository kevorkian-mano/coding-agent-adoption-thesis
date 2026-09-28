"""
Combine Accounts: merge Stage 2a seed list and Stage 2b snowball list
into a single deduplicated master file for Stage 2c.
"""

import os
import sys
import pandas as pd

SEED_FILE     = "egypt_seed_candidates.csv"
SNOWBALL_FILE = "egypt_snowball_candidates.csv"
OUTPUT_FILE   = "egypt_combined_accounts.csv"
REQUIRED_COL  = "login"


def load_and_validate(path: str, label: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f"ERROR: {label} file not found at '{path}'")
        sys.exit(1)
    df = pd.read_csv(path)
    if REQUIRED_COL not in df.columns:
        print(f"ERROR: '{REQUIRED_COL}' column missing from {label} file '{path}'")
        sys.exit(1)
    return df


def main():
    print(f"Loading {SEED_FILE} and {SNOWBALL_FILE}...")
    seed_df     = load_and_validate(SEED_FILE, "seed")
    snowball_df = load_and_validate(SNOWBALL_FILE, "snowball")

    # Tag the source before combining so we can trace back later
    seed_df["source"]     = "seed"
    snowball_df["source"] = "snowball"

    combined_df = pd.concat([seed_df, snowball_df], ignore_index=True)

    initial_count = len(combined_df)
    combined_df   = combined_df.drop_duplicates(subset=[REQUIRED_COL], keep="first")
    final_count   = len(combined_df)

    # Ensure account_type column exists (snowball output may not have it;
    # Stage 2c REST version uses this to pick the right endpoint)
    if "account_type" not in combined_df.columns:
        combined_df["account_type"] = "User"
    else:
        combined_df["account_type"] = combined_df["account_type"].fillna("User")

    combined_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\n─── Combination Summary ──────────────────────────────────")
    print(f"Seed accounts         : {len(seed_df)}")
    print(f"Snowball accounts     : {len(snowball_df)}")
    print(f"Total before dedup    : {initial_count}")
    print(f"Duplicates removed    : {initial_count - final_count}")
    print(f"Final unique accounts : {final_count}")
    print(f"Saved to '{OUTPUT_FILE}'")
    print("NEXT: run Stage2c_egypt_corpus_direct_pull.py or stage2c_fast_graphql.py")


if __name__ == "__main__":
    main()
