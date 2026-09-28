import pandas as pd
import numpy as np

np.random.seed(42)

dados = []

linhas = [101, 202, 303]

for i in range(100):

    linha = np.random.choice(linhas)

    hora = np.random.randint(5, 23)

    chuva_mm = np.random.randint(0, 31)

    temp_c = np.random.randint(16, 33)

    dia_da_semana = np.random.randint(0, 7)

    hora_pico = 1 if (
        (6 <= hora <= 9) or
        (17 <= hora <= 20)
    ) else 0

    if chuva_mm == 0:
        clima = "Clear"
    elif chuva_mm <= 5:
        clima = "Clouds"
    else:
        clima = "Rain"

    demanda = 300

    if linha == 202:
        demanda += 150

    if linha == 303:
        demanda += 300

    if hora_pico:
        demanda += 350

    demanda += chuva_mm * 10

    if chuva_mm > 15:
        demanda += 150

    if dia_da_semana >= 5:
        demanda -= 100

    demanda += np.random.randint(-50, 50)

    dados.append([
        f"2025-09-{np.random.randint(1,30):02d} {hora:02d}:00",
        linha,
        chuva_mm,
        temp_c,
        clima,
        hora_pico,
        demanda
    ])

df = pd.DataFrame(
    dados,
    columns=[
        "data_hora",
        "linha",
        "chuva_mm",
        "temp_c",
        "condicao_climatica",
        "hora_pico",
        "demanda_real"
    ]
)

df.to_csv(
    "dataset_consolidado_v2.csv",
    index=False
)

print("Arquivo gerado com sucesso!")
print(df.head())