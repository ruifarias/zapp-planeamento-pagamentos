from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

app = FastAPI()

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/pagamentos")
async def get_pagamentos():
    data = db.get_resumo_pagamentos()
    return data

@app.get("/api/resumo")
async def get_resumo():
    data = db.get_resumo_pagamentos()
    totais = data["totais_semanas"]
    wednesdays = data["wednesdays"]

    total_geral = sum(totais.values())
    num_fornecedores = len(data["pagamentos"])

    return {
        "total_geral": total_geral,
        "num_fornecedores": num_fornecedores,
        "totais_semanas": totais,
        "wednesdays": wednesdays
    }

@app.get("/api/cheques-predatados")
async def get_cheques_predatados():
    cheques_por_semana, semanas_ordenadas, totais_semanas, total_geral = db.get_cheques_predatados_por_semana()

    return {
        "cheques": cheques_por_semana,
        "semanas": semanas_ordenadas,
        "totais_semanas": totais_semanas,
        "total_geral": total_geral
    }

dist_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
