import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score

def main():
    df = pd.read_csv("model_dataset.csv", parse_dates=["date"], low_memory=False)
    print("Columns in model_dataset.csv:\n", df.columns.tolist(), "\n")

    if "burned" not in df.columns:
        raise RuntimeError("No 'burned' column in model_dataset.csv")

    non_features = {"cell_id", "date", "burned"}
    numeric = df.select_dtypes(include="number").columns.tolist()
    feature_cols = [c for c in numeric if c not in non_features]

    print(f" Detected numeric columns: {numeric}")
    print(f"Using feature columns: {feature_cols}\n")

    if not feature_cols:
        raise RuntimeError("No numeric feature columns found!")

    X = df[feature_cols].fillna(0)
    y = df["burned"].astype(int)

    stratify = y if y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    print("Classification Report:")
    print(classification_report(y_test, y_pred))

    if y_test.nunique() > 1:
        y_prob = clf.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_prob)
        print(f"ROC-AUC: {auc:.3f}")
    else:
        print("Only one class present in the test set; skipping ROC-AUC.")

if __name__ == "__main__":
    main()
