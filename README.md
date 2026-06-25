# EPC BuildControl

Sistema de controle de construção e montagem de tubulações industriais para projetos EPC.

## Stack

- **Backend**: FastAPI + PostgreSQL + SQLAlchemy
- **Frontend**: React + Vite + TailwindCSS + Recharts
- **ETL**: pandas — importa Excel (MTO, SGS, Válvulas, Juntas) e CSVs do Databook Paradox

## Módulos

| Módulo | Descrição |
|---|---|
| Dashboard | KPIs consolidados, curva S, progresso por unidade |
| Spools | Controle de fabricação e montagem por spool |
| Juntas | Rastreabilidade individual de soldas com NDT |
| MTO | Materiais do modelo 3D (~168k itens) |
| Válvulas | Controle de recebimento e disponibilidade |
| Importar | Upload de arquivos Excel com ETL automático |

## Início rápido

### Com Docker
```bash
docker compose up --build
```

### Sem Docker

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000
- App: http://localhost:5173
- Docs: http://localhost:8000/docs

## Fontes de dados

| Arquivo | Tabela | Registros |
|---|---|---|
| TYS-TUB-1_MateriaisTubulacao.xlsx | mto_items | ~168k |
| SGS-SGM_remanescente.xlsx | spools | ~41k |
| MAPA_JUNTA_PETROBRAS.xlsb | joints | ~93k |
| SGS-SGM_VALVULAS.xlsx | valves | ~340 |
| Databook Paradox (JUNTAS/TUB/SOLD/LOTERX/INCONF/RASTMAT/RESUMO) | múltiplas | ~27k |
