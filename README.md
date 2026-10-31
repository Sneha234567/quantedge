# QuantEdge

A Streamlit app for backtesting trading strategies (Buy & Hold, SMA Crossover, RSI Reversion, MACD)
on Yahoo Finance data, with user login and search history.

CI/CD: `git push -> GitHub -> Jenkins -> tests -> Docker build/push -> Kubernetes deploy`

## Run locally
    pip install -r requirements.txt
    streamlit run src/app.py

## Test
    python -m pytest -v

## Docker
    docker build -t quantedge .
    docker run -d -p 8501:8501 quantedge

## Kubernetes (Minikube)
    kubectl apply -f k8s/
    minikube service quantedge-service
