import pandas as pd, joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

# -----------------------------
# Paths
# -----------------------------
BASE = Path(__file__).resolve().parent.parent  # hr_app/
data_path = BASE.parent / "data" / "retention.csv"

# -----------------------------
# Load Data
# -----------------------------
df = pd.read_csv(data_path)

# Target variable: Attrition (Yes=1, No=0)
df["AttritionFlag"] = df["Attrition"].map({"Yes": 1, "No": 0})

# -----------------------------
# Features & Target
# -----------------------------
# Keep some useful features (you can expand later)
features = [
    "Age", "MonthlyIncome", "YearsAtCompany", "JobRole",
    "Department", "EducationField", "MaritalStatus"
]

X = df[features]
y = df["AttritionFlag"]

num_features = ["Age", "MonthlyIncome", "YearsAtCompany"]
cat_features = ["JobRole", "Department", "EducationField", "MaritalStatus"]

preprocess = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), num_features),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
    ]
)

# -----------------------------
# Model & Pipeline
# -----------------------------
model = RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced")

pipe = Pipeline(steps=[("prep", preprocess), ("clf", model)])

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
pipe.fit(X_tr, y_tr)

# -----------------------------
# Save model
# -----------------------------
out = BASE / "models" / "retention.pkl"
out.parent.mkdir(parents=True, exist_ok=True)
joblib.dump(pipe, out)

print(f"✅ Saved retention model to {out}")
