import streamlit as st
import pandas as pd
import requests
import io
import contextlib
import unittest
import tempfile
import os

st.set_page_config(page_title="Unit Converter", layout="wide")

# -----------------------------
# Theme (Light / Dark toggle)
# -----------------------------
theme = st.sidebar.selectbox("Theme", ["Light", "Dark"], index=0)
if theme == "Dark":
    st.markdown(
        """
        <style>
          :root { color-scheme: dark; }
          .stApp { background: #0b0f14; color: #e6edf3; }
          div, p, label, span, h1, h2, h3, h4, h5, h6 { color: #e6edf3 !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

st.title("🔁 Advanced Unit Converter (Streamlit)")
st.caption("Pure Python logic • History • Precision • Currency (no key) • Unit Tests")

# -----------------------------
# Categories & units
# -----------------------------
DEFAULT_CURRENCY_UNITS = ["EUR", "USD", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "TRY", "SAR", "AED", "PKR"]

CATEGORIES = {
    "Mass": ["kg", "g", "mg", "lb", "oz"],
    "Length": ["m", "cm", "mm", "km", "inch", "ft", "yd", "mile"],
    "Temperature": ["C", "F", "K"],
    "Time": ["second", "minute", "hour", "day"],
    "Area": ["m2", "cm2", "km2", "ft2", "acre"],
    "Volume": ["liter", "ml", "m3", "gallon"],
    "Speed": ["m/s", "km/h", "mph"],
    "Currency": DEFAULT_CURRENCY_UNITS,
}

MASS = {"kg": 1000, "g": 1, "mg": 0.001, "lb": 453.59237, "oz": 28.3495}             # base = gram
LENGTH = {"km": 1000, "m": 1, "cm": 0.01, "mm": 0.001, "inch": 0.0254,
          "ft": 0.3048, "yd": 0.9144, "mile": 1609.344}                               # base = meter
TIME = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}                        # base = second
AREA = {"m2": 1, "cm2": 0.0001, "km2": 1_000_000, "ft2": 0.092903, "acre": 4046.86}   # base = m²
VOLUME = {"liter": 1, "ml": 0.001, "m3": 1000, "gallon": 3.78541}                     # base = liter
SPEED = {"m/s": 1, "km/h": 0.277778, "mph": 0.44704}                                  # base = m/s

MAPS = {"Mass": MASS, "Length": LENGTH, "Time": TIME, "Area": AREA, "Volume": VOLUME, "Speed": SPEED}

# -----------------------------
# Currency (Frankfurter API, no key)
# -----------------------------
@st.cache_data(show_spinner=False)
def fetch_currency_symbols():
    try:
        data = requests.get("https://api.frankfurter.app/currencies", timeout=10).json()
        return sorted(list(data.keys()))
    except Exception:
        return DEFAULT_CURRENCY_UNITS

def currency_rate(from_u, to_u):
    url = f"https://api.frankfurter.app/latest?base={from_u}&symbols={to_u}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return float(data["rates"][to_u]), data.get("date", "")

# -----------------------------
# Temperature formulas
# -----------------------------
def convert_temperature(value, from_u, to_u):
    if from_u == "C":
        c = value
    elif from_u == "F":
        c = (value - 32) * 5 / 9
    elif from_u == "K":
        c = value - 273.15
    else:
        raise ValueError("Unknown temperature unit")

    if to_u == "C":
        return c
    elif to_u == "F":
        return c * 9 / 5 + 32
    elif to_u == "K":
        return c + 273.15
    else:
        raise ValueError("Unknown temperature unit")

def compute_result(value, category, from_u, to_u):
    if category == "Temperature":
        return convert_temperature(value, from_u, to_u)
    if category == "Currency":
        rate, _date = currency_rate(from_u, to_u)
        return value * rate
    base_value = value * MAPS[category][from_u]
    return base_value / MAPS[category][to_u]

# -----------------------------
# Session state for history
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []

# -----------------------------
# UI controls
# -----------------------------
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    category = st.selectbox("Category", list(CATEGORIES.keys()), index=0)
with col2:
    value = st.number_input("Value", value=1.0)
with col3:
    precision = st.slider("Decimal precision", 0, 10, 4)

# Units dropdowns (dynamic for Currency)
if category == "Currency":
    currency_units = fetch_currency_symbols()
    units = currency_units
else:
    units = CATEGORIES[category]

u1, u2, u3, u4 = st.columns([2, 2, 1, 1])
with u1:
    from_u = st.selectbox("From", units, index=0)
with u2:
    to_u = st.selectbox("To", units, index=1 if len(units) > 1 else 0)
with u3:
    if st.button("Swap"):
        from_u, to_u = to_u, from_u
with u4:
    convert_clicked = st.button("Convert", type="primary")

# Convert action
if convert_clicked:
    if from_u == to_u:
        st.warning("Choose different units.")
    else:
        try:
            result = compute_result(float(value), category, from_u, to_u)
            formatted = f"{result:.{precision}f}"

            meta = ""
            if category == "Currency":
                _, date = currency_rate(from_u, to_u)
                meta = f" (rates date: {date})"

            st.success(f"{value} {from_u} = {formatted} {to_u}{meta}")

            st.session_state.history.append({
                "Category": category,
                "Value": float(value),
                "From": from_u,
                "To": to_u,
                "Result": float(result),
                "Result (formatted)": formatted
            })
        except Exception as e:
            st.error(f"Error: {e}")

# History
st.subheader("📜 Conversion history")

hcol1, hcol2 = st.columns([1, 1])
with hcol1:
    if st.button("Clear history"):
        st.session_state.history = []
with hcol2:
    if st.button("Download CSV"):
        if st.session_state.history:
            df = pd.DataFrame(st.session_state.history)
            tmpdir = tempfile.mkdtemp()
            path = os.path.join(tmpdir, "conversion_history.csv")
            df.to_csv(path, index=False)
            with open(path, "rb") as f:
                st.download_button("Click to download", f, file_name="conversion_history.csv")
        else:
            st.info("No history to download yet.")

if st.session_state.history:
    st.dataframe(pd.DataFrame(st.session_state.history), use_container_width=True)
else:
    st.info("No conversions yet.")

# -----------------------------
# Unit tests (button)
# -----------------------------
st.subheader("🧪 Auto unit tests")

class ConversionTests(unittest.TestCase):
    def assertAlmost(self, a, b, tol=1e-3):
        self.assertTrue(abs(a - b) <= tol, f"Expected {b}, got {a}")

    def test_mass(self):
        self.assertAlmost(compute_result(1, "Mass", "kg", "g"), 1000, tol=1e-6)

    def test_temperature(self):
        self.assertAlmost(compute_result(0, "Temperature", "C", "F"), 32, tol=1e-6)

    def test_speed(self):
        self.assertAlmost(compute_result(100, "Speed", "km/h", "m/s"), 27.7778, tol=1e-2)

    def test_currency_soft(self):
        try:
            out = compute_result(1, "Currency", "EUR", "USD")
            self.assertTrue(out > 0)
        except Exception:
            self.skipTest("Currency API not reachable (network blocked).")

def run_tests():
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ConversionTests)
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        result = runner.run(suite)
    out = stream.getvalue()
    return ("✅ All tests PASSED!\n\n" if result.wasSuccessful() else "❌ Some tests FAILED.\n\n") + out

if st.button("Run unit tests"):
    st.code(run_tests())
