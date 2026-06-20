import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


# ===============================
# Model name mapping
# ===============================

DISPLAY_MODEL_MAP = {
    "human": "Human",

    "gemini-3-flash-preview": "Gemini-3-Flash",

    "gpt-5.5": "GPT-5.5",
    "gpt-5": "GPT-5",

    "qwen3.5-397b-a17b": "Qwen3.5-397B",
    "qwen3.5-122b-a10b": "Qwen3.5-122B",
    "qwen3.5-27b": "Qwen3.5-27B",
    "qwen3.5-35b-a3b": "Qwen3.5-35B",

    "claude-sonnet-4-6": "Claude-Sonnet-4.6",
    "claude-opus-4-7": "Claude-Opus-4.7",

    "intern-s2-preview": "Intern-S2-Preview",
    "intern-s1-pro": "Intern-S1-Pro",

    "grok-4.3": "Grok-4.3",

    "glm-4.6v": "GLM-4.6V",

    "kimi-k2.5": "Kimi-K2.5",

    "gpt-4o": "GPT-4o",

    "random": "Random",
}

ALLOWED_DISPLAY_MODELS = [
    "Human",
    "Gemini-3-Flash",
    "GPT-5.5",
    "GPT-5",
    "Qwen3.5-397B",
    "Qwen3.5-122B",
    "Qwen3.5-27B",
    "Claude-Sonnet-4.6",
    "Intern-S2-Preview",
    "Qwen3.5-35B",
    "Grok-4.3",
    "Intern-S1-Pro",
    "GLM-4.6V",
    "Claude-Opus-4.7",
    "Kimi-K2.5",
    "GPT-4o",
    "Random",
]

ALLOWED_DISPLAY_MODEL_SET = set(ALLOWED_DISPLAY_MODELS)


def normalize_model_name(name: str) -> str:
    return str(name).strip().lower()


def map_model_name(raw_model: str):
    """
    Return:
        display_model, warning

    If warning is not None, this model will be skipped.
    """
    raw_key = normalize_model_name(raw_model)
    display_model = DISPLAY_MODEL_MAP.get(raw_key)

    if display_model is None:
        return None, f"Unmapped model name: {raw_model}"

    if display_model not in ALLOWED_DISPLAY_MODEL_SET:
        return None, f"Mapped model is not allowed: {raw_model} -> {display_model}"

    return display_model, None


# ===============================
# Metric config
# ===============================

METRIC_MAP = {
    "SDR": "L1",
    "IC": "L2",
    "MA": "L3",
}

DIFFICULTY_ORDER = ["easy", "hard", "overall"]

METRIC_ORDER = ["L1", "L2", "L3", "Avg"]


# ===============================
# Utilities
# ===============================

def safe_key(name: str) -> str:
    key = re.sub(r"[^a-zA-Z0-9]+", "_", str(name).strip().lower())
    return key.strip("_")


def is_special_model(model_name: str, target: str) -> bool:
    return str(model_name).strip().lower() == target.lower()


def add_highlights(rows, fields, round_digits=3):
    """
    给每一列加 highlight_xxx_A / highlight_xxx_B。
    A = best，B = second best。
    Human 和 Random 不参与 best/second-best 计算。
    """
    normal_rows = [
        row for row in rows
        if not row.get("is_human") and not row.get("is_random")
    ]

    for field in fields:
        vals = []

        for row in normal_rows:
            value = row.get(field)
            if value is not None and not pd.isna(value):
                vals.append(round(float(value), round_digits))

        uniq = sorted(set(vals))

        if not uniq:
            continue

        best_val = uniq[-1]
        second_val = uniq[-2] if len(uniq) > 1 else None

        for row in rows:
            value = row.get(field)

            if value is None or pd.isna(value):
                continue

            value_rounded = round(float(value), round_digits)

            if np.isclose(value_rounded, best_val):
                row[f"highlight_{field}_A"] = True
            elif second_val is not None and np.isclose(value_rounded, second_val):
                row[f"highlight_{field}_B"] = True

    return rows


# ===============================
# Core table building
# ===============================

def build_testbed_rows(df: pd.DataFrame, env_name: str, round_digits=3):
    sub = df[df["env"].astype(str).str.lower() == env_name.lower()].copy()

    if sub.empty:
        raise ValueError(f"No rows found for env={env_name}")

    missing_metrics = [m for m in METRIC_MAP.keys() if m not in sub.columns]
    if missing_metrics:
        raise ValueError(f"Missing metrics in CSV: {missing_metrics}")

    # Normalize difficulty
    sub["difficulty_norm"] = sub["difficulty"].astype(str).str.lower()

    # Convert metrics to numeric
    for metric in METRIC_MAP.keys():
        sub[metric] = pd.to_numeric(sub[metric], errors="coerce")

    # Map model names and filter models
    mapped_models = []
    missing_model_warnings = []

    for raw_model in sub["model"].astype(str):
        display_model, warning = map_model_name(raw_model)

        if warning is not None:
            missing_model_warnings.append(warning)
            mapped_models.append(None)
        else:
            mapped_models.append(display_model)

    sub["display_model"] = mapped_models
    sub = sub[sub["display_model"].notna()].copy()

    if missing_model_warnings:
        print(f"\n[Warning] Some models are skipped in env={env_name}:")
        for warning in sorted(set(missing_model_warnings)):
            print("  -", warning)

    if sub.empty:
        raise ValueError(
            f"No valid models left for env={env_name}. "
            "Please check DISPLAY_MODEL_MAP and ALLOWED_DISPLAY_MODELS."
        )

    metrics = list(METRIC_MAP.keys())

    # easy / hard
    res = sub.groupby(["display_model", "difficulty_norm"])[metrics].mean()

    # overall
    overall = sub.groupby("display_model")[metrics].mean()
    overall["difficulty_norm"] = "overall"
    overall = overall.set_index("difficulty_norm", append=True)

    res = pd.concat([res, overall])

    # Rename SDR/IC/MA -> L1/L2/L3
    res = res.rename(columns=METRIC_MAP)

    # Avg = mean of L1, L2, L3
    res["Avg"] = res[METRIC_ORDER[:-1]].mean(axis=1)

    # MultiIndex columns: metric x difficulty
    wide = res.unstack("difficulty_norm")

    fields = []
    for difficulty in DIFFICULTY_ORDER:
        for metric in METRIC_ORDER:
            fields.append(f"{difficulty}_{metric.lower()}")

    rows = []

    for display_model in wide.index:
        row = {
            "model": display_model,
            "source_model": display_model,
            "is_human": is_special_model(display_model, "Human"),
            "is_random": is_special_model(display_model, "Random"),
            "is_api": False,
        }

        for difficulty in DIFFICULTY_ORDER:
            for metric in METRIC_ORDER:
                field = f"{difficulty}_{metric.lower()}"

                try:
                    value = wide.loc[display_model, (metric, difficulty)]
                except KeyError:
                    value = None

                if value is None or pd.isna(value):
                    row[field] = None
                else:
                    row[field] = round(float(value), round_digits)

        rows.append(row)

    # 保持原逻辑：按 Overall Avg 降序排序
    rows.sort(
        key=lambda x: (
            x.get("overall_avg") is not None,
            x.get("overall_avg") if x.get("overall_avg") is not None else -999999,
        ),
        reverse=True,
    )

    rows = add_highlights(rows, fields, round_digits=round_digits)

    return rows


# ===============================
# Main
# ===============================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="results/raw.csv")
    parser.add_argument("--out", default="static/js/vk_self_table_data.js")
    parser.add_argument(
        "--envs",
        nargs="+",
        default=None,
        help="VK-Self testbed env names, e.g. 2d sc2 isaac",
    )
    parser.add_argument("--round", type=int, default=3)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)

    required_cols = {"model", "env", "difficulty", "seed"}
    missing_cols = required_cols - set(df.columns)

    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    envs = args.envs

    if envs is None:
        envs = sorted(df["env"].dropna().astype(str).unique().tolist())

    payload = {}

    for env in envs:
        key = safe_key(env)
        rows = build_testbed_rows(df, env, round_digits=args.round)

        payload[key] = {
            "label": f"VK-Self / {env}",
            "env": env,
            "data": rows,
        }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    js = "window.VK_SELF_TABLES = "
    js += json.dumps(payload, ensure_ascii=False, indent=2)
    js += ";\n"

    out_path.write_text(js, encoding="utf-8")

    print(f"\nWrote {args.out}")
    print(f"Generated envs: {', '.join(envs)}")


if __name__ == "__main__":
    main()