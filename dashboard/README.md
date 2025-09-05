# Dashboard de Mapeamento Temático dos TCCs – CC/UFCG

Aplicação Streamlit para explorar os resultados de modelagem de tópicos (BERTopic alt) sobre TCCs: visão geral, busca de orientadores, filtro por tema, perfil de orientador e evolução temporal dos temas.

## Requisitos

- Python 3.10+  
- Ambiente virtual já existente no projeto: `envs\comparison`
- Arquivo de dependências na raiz do repositório: `requirements_dashboard.txt`
- Artefatos exportados pelo notebook `notebooks/bertopic/export_dashboard.ipynb` em:
  ```
  data/exports/dashboard/
      docs.parquet
      topics.parquet
      topics_current.parquet   (opcional)
      doc_topics.parquet
      topic_trends.parquet
      advisor_profiles.parquet
      advisor_topics.parquet
      _manifest.json
  ```

> Observação: o app descobre a raiz do projeto subindo diretórios até encontrar `data/` e `notebooks/`. Não é necessário configurar paths manualmente se a estrutura padrão do repositório for mantida.

## Instalação

1. Ative o ambiente `comparison`:

```powershell
cd "C:\Users\User\Desktop\TCC\Notebooks locais\analise_topicos_tcc"
.\envs\comparison\Scripts\activate
```

2. Instale as dependências do dashboard:

```powershell
pip install -r requirements_dashboard.txt
```

## Execução

1. Entre na pasta do app:

```powershell
cd dashboard
```

2. Rode o Streamlit:

```powershell
streamlit run app.py
```

3. Abra no navegador o endereço exibido no terminal (por padrão, `http://localhost:8501`).

## Funcionalidades

- **Visão geral**: métricas principais e gráficos de participação média por tema e distribuição de TCCs por ano.  
- **Pesquisar orientadores**: busca por nome.  
- **Filtrar TCCs por tema**: lista de TCCs, evolução temporal e metadados.  
- **Perfil do orientador**: resumo de atuação, temas principais e trabalhos orientados.  
- **Evolução de temas**: comparação de até 6 temas ao longo do tempo.

## Problemas comuns

- **Erro de leitura de Parquet**: instale `pyarrow` no ambiente `comparison`  
  ```pip install pyarrow```
- **Arquivos ausentes em `data/exports/dashboard/`**: execute o notebook `export_dashboard.ipynb` para gerá-los.
- **Porta em uso**: rode o Streamlit com outra porta  
  ```streamlit run app.py --server.port 8502```