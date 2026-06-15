import pyodbc
from datetime import datetime, timedelta
from collections import defaultdict
import os

def get_connection():
    conn_str = (
        r'Driver={ODBC Driver 18 for SQL Server};'
        r'Server=CLASSICO-PC\SQLEXPRESS;'
        r'Database=DBClassico;'
        r'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

def calculate_week_number(data_vencimento):
    """Calcula a semana de vencimento baseado na data.
    Semana 0: Vencido (data <= hoje)
    Semana 1-N: Próximas semanas de quarta a quarta
    """
    today = datetime.now().date()

    if isinstance(data_vencimento, datetime):
        data_vencimento = data_vencimento.date()

    if data_vencimento <= today:
        return 0

    days_until = (data_vencimento - today).days
    week_number = (days_until + 6) // 7

    return max(1, week_number)

def get_wednesday_dates(num_weeks=13):
    """Retorna as datas das próximas quartas-feiras (data de pagamento)."""
    today = datetime.now().date()
    weekday = today.weekday()

    days_to_wednesday = (2 - weekday) % 7
    if days_to_wednesday == 0:
        days_to_wednesday = 7

    wednesdays = []
    current_wednesday = today + timedelta(days=days_to_wednesday)

    for i in range(num_weeks):
        wednesdays.append(current_wednesday)
        current_wednesday += timedelta(days=7)

    return wednesdays

def get_pagamentos_por_semana():
    """Retorna documentos agrupados por semana e fornecedor."""
    conn = get_connection()
    cursor = conn.cursor()

    ano_atual = datetime.now().year

    query = f"""
    SELECT
        doc.Codigo_Conta,
        doc.Tipo_Movimento,
        doc.Numero_Documento,
        doc.Data_Vencimento,
        CASE doc.Tipo_Movimento
            WHEN 'C' THEN doc.Valor_por_Regularizar
            WHEN 'D' THEN -doc.Valor_Por_Regularizar
        END as Valor_Por_Regularizar,
        COALESCE(poc.Descricao_Conta, CONCAT('Conta ', doc.Codigo_Conta)) as Nome_Fornecedor
    FROM TB0001CntDocReg doc
    LEFT JOIN TB0001CntPOC poc ON doc.Codigo_Conta = poc.Codigo_Conta AND poc.Ano = {ano_atual}
    WHERE (doc.codigo_conta LIKE '22%' OR doc.codigo_conta LIKE '271%')
    ORDER BY doc.Codigo_Conta, doc.Data_Vencimento
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    pagamentos = defaultdict(lambda: defaultdict(float))
    documentos_por_semana = defaultdict(lambda: defaultdict(int))

    for row in rows:
        codigo_conta = row[0]
        valor = row[4]
        data_vencimento = row[3]
        nome_fornecedor = row[5]

        if valor is None or valor == 0:
            continue

        week_num = calculate_week_number(data_vencimento)

        pagamentos[codigo_conta][f"semana_{week_num}"] += valor
        pagamentos[codigo_conta]["nome"] = nome_fornecedor
        documentos_por_semana[codigo_conta][f"semana_{week_num}"] += 1

    conn.close()

    return dict(pagamentos), get_wednesday_dates()

def get_resumo_pagamentos():
    """Retorna totais por semana."""
    pagamentos, wednesdays = get_pagamentos_por_semana()

    totais_semanas = defaultdict(float)

    for fornecedor_data in pagamentos.values():
        for key, valor in fornecedor_data.items():
            if key != "nome":
                totais_semanas[key] += valor

    return {
        "pagamentos": pagamentos,
        "totais_semanas": dict(totais_semanas),
        "wednesdays": [d.isoformat() for d in wednesdays]
    }
