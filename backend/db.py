import pyodbc
from datetime import datetime, timedelta
from collections import defaultdict
import os

def get_connection():
    server = os.getenv('DB_SERVER', 'TSERVER\\SQLSERVER')
    database = os.getenv('DB_DATABASE', 'DBClassico')
    user = os.getenv('DB_USER', 'GIWINDOWS')
    password = os.getenv('DB_PASSWORD', 'GIWINDOWS')

    conn_str = (
        r'Driver={ODBC Driver 18 for SQL Server};'
        f'Server={server};'
        f'Database={database};'
        f'UID={user};'
        f'PWD={password};'
        r'TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str)

def calculate_week_number(data_vencimento):
    """Calcula a semana ISO de vencimento.
    Retorna string no formato 'XX_YYYY' (semana_ano).
    Faturas vencidas (data <= hoje) são agrupadas na semana atual.
    """
    today = datetime.now().date()

    if isinstance(data_vencimento, datetime):
        data_vencimento = data_vencimento.date()

    # Se a fatura já venceu, agrupa na semana atual
    if data_vencimento <= today:
        iso_calendar = today.isocalendar()
        year = iso_calendar[0]  # Ano
        week_num = iso_calendar[1]  # Semana
        return f"{week_num}_{year}"

    # Caso contrário, usa a semana de vencimento
    iso_calendar = data_vencimento.isocalendar()
    year = iso_calendar[0]
    week_num = iso_calendar[1]
    return f"{week_num}_{year}"

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
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Erro de conexao: {e}")
        return {}, [], 0.0

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

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao executar query: {e}")
        conn.close()
        return {}, [], 0.0

    pagamentos = defaultdict(lambda: defaultdict(float))
    documentos_por_semana = defaultdict(lambda: defaultdict(int))

    today = datetime.now().date()
    total_vencido = 0.0

    for row in rows:
        codigo_conta = row[0]
        valor = float(row[4])
        data_vencimento = row[3]
        nome_fornecedor = row[5]

        if valor is None or valor == 0:
            continue

        week_num = calculate_week_number(data_vencimento)

        # Somar faturas efetivamente vencidas (data de vencimento <= hoje)
        venc = data_vencimento.date() if isinstance(data_vencimento, datetime) else data_vencimento
        if venc is not None and venc <= today:
            total_vencido += valor

        pagamentos[codigo_conta][f"semana_{week_num}"] += valor
        pagamentos[codigo_conta]["nome"] = nome_fornecedor
        documentos_por_semana[codigo_conta][f"semana_{week_num}"] += 1

    conn.close()

    return dict(pagamentos), get_wednesday_dates(), total_vencido

def get_resumo_pagamentos():
    """Retorna totais por semana com dados formatados."""
    pagamentos, wednesdays, total_vencido = get_pagamentos_por_semana()

    totais_semanas = defaultdict(float)
    todas_as_semanas = set()

    # Calcular semanas e totais
    for fornecedor_data in pagamentos.values():
        total_fornecedor = 0
        for key, valor in fornecedor_data.items():
            if key != "nome" and key != "total_divida" and key.startswith("semana_"):
                totais_semanas[key] += valor
                total_fornecedor += valor
                todas_as_semanas.add(key)
        fornecedor_data["total_divida"] = total_fornecedor

    # Ordenar semanas por ano e depois por número de semana
    semanas_ordenadas = sorted(todas_as_semanas, key=lambda x: (
        int(x.replace("semana_", "").split("_")[1]),
        int(x.replace("semana_", "").split("_")[0])
    ))

    return {
        "pagamentos": pagamentos,
        "totais_semanas": dict(totais_semanas),
        "wednesdays": [d.isoformat() for d in wednesdays],
        "semanas": semanas_ordenadas,
        "total_vencido": total_vencido
    }

def get_cheques_predatados_por_semana():
    """Retorna cheques pré-datados agrupados por semana de vencimento."""
    try:
        conn = get_connection()
    except Exception as e:
        print(f"Erro de conexao: {e}")
        return {}, []

    cursor = conn.cursor()

    query = """
    SELECT
        Codigo_Entidade,
        Data_Documento AS Data_Emissao,
        Numero_Documento,
        Valor,
        Entidade_Sacada,
        Local_Emissao
    FROM TB0001TesMovCaixa
    WHERE Codigo_Movimento_Caixa = 'CHP'
        AND Conciliado = 'N'
    ORDER BY Data_Documento
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Erro ao executar query: {e}")
        conn.close()
        return {}, []

    cheques_por_semana = defaultdict(lambda: defaultdict(list))
    totais_semanas = defaultdict(float)
    todas_as_semanas = set()

    for row in rows:
        codigo_entidade = row[0]
        data_documento = row[1]
        numero_documento = row[2]
        valor = float(row[3]) if row[3] else 0.0
        entidade_sacada = row[4]
        local_emissao = row[5]

        if valor == 0:
            continue

        week_num = calculate_week_number(data_documento)
        todas_as_semanas.add(week_num)

        cheques_por_semana[codigo_entidade][f"semana_{week_num}"].append({
            "numero_documento": numero_documento,
            "data_documento": data_documento.isoformat() if hasattr(data_documento, 'isoformat') else str(data_documento),
            "valor": -valor,  # Negativo para representar divida
            "entidade_sacada": entidade_sacada,
            "local_emissao": local_emissao
        })

        totais_semanas[f"semana_{week_num}"] += valor

    # Ordenar semanas
    semanas_ordenadas = sorted(todas_as_semanas, key=lambda x: (
        int(x.replace("semana_", "").split("_")[1]),
        int(x.replace("semana_", "").split("_")[0])
    ))

    conn.close()

    return dict(cheques_por_semana), semanas_ordenadas, dict(totais_semanas)
