"""Write numbers.tex from backend/ml_training/research/results_v2.json, so no number in the paper is typed by hand.

    python docs/paper/v2/make_numbers.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "..", "..", "..", "backend", "ml_training", "research", "results_v2.json")))
M = {}


def pct(x):
    return f"{100 * x:.1f}"


def add(name, value):
    assert name.isalpha(), name
    M[name] = value


x1 = R["X1_main"]
for tag, key in (("Rep", "v1_reported"), ("Dep", "v1"), ("Two", "v2")):
    for ds, dn in (("real_test", "Real"), ("challenge", "Chal"), ("hinglish_b_final", "HinB"), ("hinglish_a_dev_check", "HinA")):
        m = x1[ds][key]["final"]
        add(f"f{dn}{tag}", pct(m["f1"]))
        add(f"fpr{dn}{tag}", pct(m["fpr"]))
    m = x1["real_test"][key]["final"]
    add(f"accReal{tag}", pct(m["accuracy"]))
    add(f"ciLoReal{tag}", pct(m["f1_ci"][0]))
    add(f"ciHiReal{tag}", pct(m["f1_ci"][1]))
add("aucRealTwo", f"{x1['real_test']['v2']['final']['roc_auc']:.3f}")
add("pReal", f"{x1['real_test']['mcnemar_final_v1_vs_v2']['p_value']:.2f}")
_p = x1["hinglish_b_final"]["mcnemar_final_v1_vs_v2"]["p_value"]
add("pHinB", "$<$0.001" if _p < 0.001 else f"{_p:.3f}")
add("nReal", str(x1["real_test"]["v2"]["final"]["n"]))
add("nChal", str(x1["challenge"]["v2"]["final"]["n"]))

x2 = R["X2_adversarial"]
names = {"homoglyph": "Homo", "zero_width": "Zero", "spaced_letters": "Spaced", "leetspeak": "Leet", "defanged_url": "Defang", "combined": "Combo", "clean": "Clean"}
for k, n in names.items():
    add(f"rec{n}One", pct(x2[k]["v1"]["recall"]))
    add(f"rec{n}Two", pct(x2[k]["v2"]["recall"]))
    add(f"fprAdv{n}One", pct(x2[k]["v1"]["fpr"]))
    add(f"fprAdv{n}Two", pct(x2[k]["v2"]["fpr"]))
    if "messages_changed" in x2[k]:
        add(f"chg{n}", pct(x2[k]["messages_changed"]))

x3 = R["X3_temporal"]
add("recFuture", pct(x3["temporal"]["recall_future_scams"]))
add("recRandMean", pct(x3["random_holdout_mean_recall"]))
add("recRandMin", pct(min(r["recall"] for r in x3["random_holdout"])))
add("recRandMax", pct(max(r["recall"] for r in x3["random_holdout"])))
add("nFutureMsgs", str(x3["future_scam_messages"]))
add("nFutureCamps", str(x3["future_campaigns"]))
add("nDatedCamps", str(x3["dated_campaigns"]))

x4 = R["X4_calibration"]
add("eceClf", f"{x4['ece_classifier']:.3f}")
add("eceFinal", f"{x4['ece_final']:.3f}")
b = x4["review_band"]["0.3-0.7"]
add("bandShare", pct(b["share_flagged_for_review"]))
add("bandErrIn", str(b["errors_inside"]))
add("bandErrTotal", str(b["total_errors"]))
add("bandAccOut", pct(b["accuracy_outside"]))

x5 = R["X5_fusion_ablation"]
for ds, dn in (("real_test", "Real"), ("challenge", "Chal"), ("hinglish_b_final", "HinB")):
    for v, vn in (("classifier_only", "Clf"), ("rules_only", "Rules"), ("plus_intents", "Intents"), ("plus_protective", "Prot"), ("full", "Full")):
        add(f"abl{dn}{vn}F", pct(x5[ds][v]["f1"]))
        add(f"abl{dn}{vn}Fpr", pct(x5[ds][v]["fpr"]))

x6 = R["X6_rule_baselines"]
add("linkRealF", pct(x6["real_test"]["has_link"]["f1"]))
add("linkRealFpr", pct(x6["real_test"]["has_link"]["fpr"]))
add("linkPhoneRealF", pct(x6["real_test"]["has_link_or_phone"]["f1"]))
add("nNoLink", str(x6["real_test"]["scams_without_link"]["n"]))
add("recNoLink", pct(x6["real_test"]["scams_without_link"]["recall_scamguard_v2"]))
add("linkCrossF", pct(x6["cross_domain_dataset_b"]["has_link"]["f1"]))

x7 = R["X7_latency"]
add("msPerMsg", f"{x7['ms_per_message_cpu']:.2f}")

x8 = R["X8_real_hindi"]
for tag, key in (("Rep", "v1_reported"), ("Dep", "v1"), ("Two", "v2")):
    m = x8[key]
    add(f"fRH{tag}", pct(m["f1"]))
    add(f"fprRH{tag}", pct(m["fpr"]))
    add(f"recRH{tag}", pct(m["recall"]))
    add(f"precRH{tag}", pct(m["precision"]))
    add(f"ciLoRH{tag}", pct(m["f1_ci"][0]))
    add(f"ciHiRH{tag}", pct(m["f1_ci"][1]))
    add(f"grpRH{tag}", pct(m["group_accuracy"]))
add("pRH", f"{x8['mcnemar_v1_vs_v2']['p_value']:.2f}")
add("nRH", str(x8["messages"]))
add("nRHScam", str(x8["scam"]))
add("nRHGen", str(x8["genuine"]))
add("nRHGroups", str(x8["groups"]))

d = R["data"]
add("nTrain", f"{d['train_rows_v1']:,}".replace(",", "{,}"))
add("nHinTrain", f"{d['hinglish_train_rows']:,}".replace(",", "{,}"))
add("vocabTwo", f"{d['vocabulary']['v2']:,}".replace(",", "{,}"))

T = json.load(open(os.path.join(HERE, "..", "..", "..", "backend", "ml_training", "research", "transformer_results.json")))
for mk, mn in (("muril", "Mu"), ("xlmr", "Xl")):
    for ds, dn in (("real_test", "Real"), ("challenge", "Chal"), ("hinglish_b_final", "HinB"), ("real_hindi", "RH")):
        t = T["models"][mk]["tests"][ds]
        add(f"t{mn}{dn}F", pct(t["classifier"]["f1"]))
        add(f"t{mn}{dn}Fpr", pct(t["classifier"]["fpr"]))
        add(f"t{mn}{dn}FusF", pct(t["fused"]["f1"]))
        add(f"t{mn}{dn}FusFpr", pct(t["fused"]["fpr"]))
        add(f"t{mn}{dn}TwoF", pct(t["two_stage"]["f1"]))
        p_ = t["mcnemar_fused_vs_lr_v2"]["p_value"]
        add(f"t{mn}{dn}P", "$<$0.001" if p_ < 0.001 else f"{p_:.2f}")
    add(f"t{mn}Ms", f"{T['models'][mk]['tests']['real_test']['ms_per_message']:.1f}")
    c = T["T1_cross_domain"]["transformers"][mk]
    add(f"t{mn}CrossFull", pct(c["train_A"]["full_B_f1"]))
    add(f"t{mn}CrossTen", pct(c["train_A_plus_10pct_B"]["B_test_f1"]))
    for ds, dn in (("real_test", "Real"), ("challenge", "Chal"), ("hinglish_b_final", "HinB"), ("real_hindi", "RH")):
        pass
for ds, dn in (("real_test", "Real"), ("challenge", "Chal"), ("hinglish_b_final", "HinB"), ("real_hindi", "RH")):
    add(f"tLr{dn}F", pct(T["lr_v2"][ds]["final"]["f1"]))
    add(f"tLr{dn}Fpr", pct(T["lr_v2"][ds]["final"]["fpr"]))
xr = T["models"]["xlmr"]["tests"]["real_hindi"]["classifier"]
add("tXlRHciLo", pct(xr["f1_ci"][0])); add("tXlRHciHi", pct(xr["f1_ci"][1]))
add("tXlRHRec", pct(xr["recall"])); add("tXlRHPrec", pct(xr["precision"]))
lr = T["lr_v2"]["real_hindi"]["final"]
add("tLrRHciLo", pct(lr["f1_ci"][0])); add("tLrRHciHi", pct(lr["f1_ci"][1]))
mc = T["models"]["xlmr"]["tests"]["real_hindi"]["mcnemar_fused_vs_lr_v2"]
add("tXlRHWins", str(mc["a_wrong_b_right"])); add("tXlRHLosses", str(mc["a_right_b_wrong"]))
add("tLrCrossFull", pct(T["T1_cross_domain"]["lr_reference"]["train_A_test_full_B"]))
add("tLrCrossTen", pct(T["T1_cross_domain"]["lr_reference"]["adapt_10pct_B_test_mean_3_seeds"]))
add("tTrainRows", f"{T['protocol']['train_rows']:,}".replace(",", "{,}"))

with open(os.path.join(HERE, "numbers.tex"), "w") as fh:
    fh.write("% Generated by make_numbers.py from results_v2.json. Do not edit.\n")
    for k, v in sorted(M.items()):
        fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
print(len(M), "macros")
