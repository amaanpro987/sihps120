install:
	python -m pip install -r requirements_premium.txt
init:
	python run_premium.py
app:
	streamlit run app_premium.py
api:
	uvicorn api:app --host 0.0.0.0 --port 8000
