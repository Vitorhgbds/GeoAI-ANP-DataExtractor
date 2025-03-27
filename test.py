# Re-import necessary libraries
import pandas as pd

# Load the newly uploaded dataset
file_path = "./Tabela_pocos_2025_Fevereiro_23.csv"
df = pd.read_csv(file_path, delimiter=",", encoding="utf-8")

print(df.info())

# Filtering only terrestrial wells
df_terrestrial = df[df["TERRA_MAR"].str.contains("T", na=False, case=False)]

# Query 1: Total terrestrial wells per basin
query_1 = df_terrestrial.groupby("BACIA").agg(
    Total_Wells=("POCO", "nunique")
).reset_index()

# Query 2: Terrestrial wells with Composite Logs per basin
query_2 = df_terrestrial[df_terrestrial["PC"].str.contains("EXISTE", na=False, case=False)].groupby("BACIA").agg(
    Composite_Logs=("POCO", "nunique")
).reset_index()

# Query 3: Terrestrial wells with Conventional Logs per basin
query_3 = df_terrestrial[df_terrestrial["PERFIS_CONVENCIONAIS"].str.contains("EXISTE", na=False, case=False)].groupby("BACIA").agg(
    Conventional_Logs=("POCO", "nunique")
).reset_index()

# Query 4: Wells with both Composite and Conventional Logs per basin
query_4 = df_terrestrial[
    df_terrestrial["PC"].str.contains("EXISTE", na=False, case=False) &
    df_terrestrial["PERFIS_CONVENCIONAIS"].str.contains("EXISTE", na=False, case=False)
].groupby("BACIA").agg(
    Both_Logs=("POCO", "nunique")
).reset_index()

# Query 5: Wells with Composite Logs but missing Conventional Logs per basin
query_5 = df_terrestrial[
    df_terrestrial["PC"].str.contains("EXISTE", na=False, case=False) &
    ~df_terrestrial["PERFIS_CONVENCIONAIS"].str.contains("EXISTE", na=False, case=False)
].groupby("BACIA").agg(
    Only_Composite=("POCO", "nunique")
).reset_index()

# Display results
print(f"Total Terrestrial Wells per Basin {query_1}")
print(f"Wells with Composite Logs per Basin {query_2}")
print(f"Wells with Conventional Logs per Basin {query_3}")
print(f"Wells with Both Logs per Basin {query_4}")
print(f"Wells with Only Composite Logs per Basin {query_5}")

import pandas as pd

# Creating the consolidated table
df_summary = pd.DataFrame({
    "BACIA": [
        "Acre", "Alagoas", "Almada", "Amazonas", "Araripe", "Barreirinhas", "Bragana - Vizeu", "Camamu", "Campos",
        "Cumuruxatiba", "Esprito Santo", "Jatob", "Jequitinhonha", "Maraj", "Mucuri", "Pantanal", "Paran",
        "Parecis - Alto Xingu", "Parnaba", "Pelotas", "Pernambuco - Paraba", "Potiguar", "Recncavo",
        "Rio do Peixe", "Sergipe", "So Francisco", "So Lus", "Solimes", "Tacutu", "Tucano Central",
        "Tucano Norte", "Tucano Sul"
    ],
    "TOTAL POCOS": [
        11, 901, 6, 242, 2, 97, 2, 36, 1, 1, 1794, 2, 6, 18, 42, 13, 125, 7, 252, 8, 3, 9155, 6107, 5, 4349,
        59, 19, 367, 2, 13, 5, 136
    ],
    "TOTAL PC": [
        11, 328, 6, 217, 2, 79, 2, 32, 1, 1, 713, 2, 6, 18, 36, None, 123, 7, 159, 1, 3, 1087, 1239, 5, 567,
        56, 19, 212, 2, 13, 5, 100
    ],
    "TOTAL PERFIL CONVENCIONAL": [
        None, 194, None, 29, None, 3, None, None, None, None, 510, None, None, None, 13, None, 7, 4, 200, None,
        None, 3537, 1107, 5, 1328, 36, 1, 156, None, None, None, 5
    ],
    "TOTAL PC AND PERFIL CONVENCIONAL": [
        None, 43, None, 20, None, 3, None, None, None, None, 175, None, None, None, 13, None, 7, 4, 118, None,
        None, 360, 223, 5, 111, 36, 1, 71, None, None, None, 3
    ],
    "TOTAL PC AND NOT PERFIL CONVENCIONAL": [
        11, 285, 6, 197, 2, 76, 2, 32, 1, 1, 538, 2, 6, 18, 23, None, 116, 3, 41, 1, 3, 727, 1016, None, 456,
        20, 18, 141, 2, 13, 5, 97
    ]
})

print(df_summary)

df_summary.to_csv("summary.csv", index=False)