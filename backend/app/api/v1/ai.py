"""AI assistant endpoint — usa Claude com tool use para consultar o banco."""

import os, json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from ...database import get_db
from ...api.deps import get_current_user

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["ai"])


class ChatRequest(BaseModel):
    message: str


TOOLS = [
    {
        "name": "get_kpi_overview",
        "description": "Retorna KPIs gerais do projeto: totais de spools por status, juntas, pesos, holds.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "query_spools",
        "description": "Consulta spools com filtros opcionais. Retorna lista com spool_key, status, peso, unidade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "NAO_INICIADO|EM_FABRICACAO|FABRICADO|EM_CAMPO|MONTADO|TESTADO"},
                "hold": {"type": "boolean"},
                "unit_code": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "query_joints",
        "description": "Consulta juntas. Retorna contagens por status, material, inspeção.",
        "input_schema": {
            "type": "object",
            "properties": {
                "isometrico": {"type": "string"},
                "status": {"type": "string"},
                "material": {"type": "string", "description": "AC|AL|AI|ST"},
                "is_repair": {"type": "boolean"},
                "requires_tt": {"type": "boolean"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_welder_performance",
        "description": "Retorna performance dos soldadores: nome, SIN, total de juntas, reparos, índice de reparo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "order_by": {"type": "string", "description": "repair_index|total_joints", "default": "total_joints"},
            },
        },
    },
    {
        "name": "get_ncr_list",
        "description": "Lista não-conformidades (NCR/RNC) do projeto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "released": {"type": "boolean"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_holds_list",
        "description": "Lista spools em hold com motivo e unidade.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

SYSTEM_PROMPT = """Você é o assistente de IA do EPC BuildControl, sistema de gestão de construção e montagem de tubulações da UGH (Unidade de Geração de Hidrogênio) — projeto Toyo/Petrobras.

Você tem acesso a dados em tempo real de:
- ~41.000 spools (status de fabricação e montagem)
- ~93.000 juntas soldadas (status, END, soldadores)
- ~340 válvulas industriais
- Soldadores qualificados
- Não-conformidades (RNC)

Responda sempre em português. Seja preciso com números. Use os dados das ferramentas para embasar todas as respostas.
Quando o usuário pedir análises, use múltiplas consultas para construir uma resposta completa."""


def _run_tool(name: str, inputs: dict, project_id: int, db: Session) -> str:
    pid = project_id

    if name == "get_kpi_overview":
        r = db.execute(text("""
            SELECT COUNT(*) total_spools,
                   COUNT(*) FILTER (WHERE status='FABRICADO') fabricado,
                   COUNT(*) FILTER (WHERE status='MONTADO') montado,
                   COUNT(*) FILTER (WHERE status='TESTADO') testado,
                   COUNT(*) FILTER (WHERE hold=TRUE) em_hold,
                   COALESCE(SUM(weight_kg),0) peso_total_kg
            FROM spools WHERE project_id=:pid
        """), {"pid": pid}).mappings().first()
        j = db.execute(text("""
            SELECT COUNT(*) total,
                   COUNT(*) FILTER (WHERE status='30_LIBERADA') liberadas,
                   COUNT(*) FILTER (WHERE is_repair=TRUE) reparos,
                   COUNT(*) FILTER (WHERE requires_tt=TRUE) com_tt
            FROM joints WHERE project_id=:pid
        """), {"pid": pid}).mappings().first()
        return json.dumps({"spools": dict(r), "joints": dict(j)}, default=str)

    if name == "query_spools":
        clauses, params = ["s.project_id=:pid"], {"pid": pid}
        if inputs.get("status"): clauses.append("s.status=:st"); params["st"] = inputs["status"]
        if inputs.get("hold") is not None: clauses.append("s.hold=:hold"); params["hold"] = inputs["hold"]
        if inputs.get("unit_code"): clauses.append("u.code=:uc"); params["uc"] = inputs["unit_code"]
        limit = inputs.get("limit", 20)
        rows = db.execute(text(f"""
            SELECT s.spool_key, s.status, s.weight_kg, s.joints_total, s.hold, s.hold_reason,
                   u.code unit_code
            FROM spools s LEFT JOIN units u ON u.id=s.unit_id
            WHERE {' AND '.join(clauses)} ORDER BY s.spool_key LIMIT {limit}
        """), params).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)

    if name == "query_joints":
        clauses, params = ["project_id=:pid"], {"pid": pid}
        if inputs.get("isometrico"): clauses.append("isometrico=:iso"); params["iso"] = inputs["isometrico"]
        if inputs.get("status"): clauses.append("status=:st"); params["st"] = inputs["status"]
        if inputs.get("material"): clauses.append("material::text=:mat"); params["mat"] = inputs["material"]
        if inputs.get("is_repair") is not None: clauses.append("is_repair=:rep"); params["rep"] = inputs["is_repair"]
        if inputs.get("requires_tt") is not None: clauses.append("requires_tt=:tt"); params["tt"] = inputs["requires_tt"]
        limit = inputs.get("limit", 20)
        rows = db.execute(text(f"""
            SELECT isometrico, spool, junta, joint_type, diameter_mm, material::text, status::text,
                   is_repair, requires_tt, dt_soldagem, dt_lib_end
            FROM joints WHERE {' AND '.join(clauses)} ORDER BY isometrico, spool, junta LIMIT {limit}
        """), params).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)

    if name == "get_welder_performance":
        order = "j.total_joints DESC" if inputs.get("order_by") != "repair_index" else "repair_rate DESC"
        limit = inputs.get("limit", 10)
        rows = db.execute(text(f"""
            SELECT w.sin, w.name, w.company,
                   COUNT(jt.id) total_joints,
                   COUNT(jt.id) FILTER (WHERE jt.is_repair=TRUE) reparos,
                   ROUND(COUNT(jt.id) FILTER (WHERE jt.is_repair=TRUE)::numeric /
                         NULLIF(COUNT(jt.id),0)*100,1) repair_rate
            FROM welders w
            LEFT JOIN joints jt ON (jt.welder_root_id=w.id OR jt.welder_fill_id=w.id)
            WHERE w.project_id=:pid
            GROUP BY w.sin, w.name, w.company
            ORDER BY {order} LIMIT {limit}
        """), {"pid": pid}).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)

    if name == "get_ncr_list":
        clauses, params = ["project_id=:pid"], {"pid": pid}
        if inputs.get("released") is not None: clauses.append("released=:rel"); params["rel"] = inputs["released"]
        limit = inputs.get("limit", 20)
        rows = db.execute(text(f"""
            SELECT rnc_number, description, dt_generated, released, dt_released
            FROM nonconformances WHERE {' AND '.join(clauses)}
            ORDER BY dt_generated DESC LIMIT {limit}
        """), params).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)

    if name == "get_holds_list":
        rows = db.execute(text("""
            SELECT s.spool_key, s.hold_reason, s.material::text, s.weight_kg, u.code unit_code
            FROM spools s LEFT JOIN units u ON u.id=s.unit_id
            WHERE s.project_id=:pid AND s.hold=TRUE ORDER BY s.spool_key
        """), {"pid": pid}).mappings().all()
        return json.dumps([dict(r) for r in rows], default=str)

    return json.dumps({"error": f"tool {name} not found"})


@router.post("/chat")
def chat(
    project_id: int,
    req: ChatRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {"reply": "❌ ANTHROPIC_API_KEY não configurada. Adicione ao .env do backend."}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        messages = [{"role": "user", "content": req.message}]

        for _ in range(5):  # max 5 tool loops
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                return {"reply": "\n".join(text_blocks)}

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _run_tool(block.name, block.input, project_id, db)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            if not tool_results:
                break
            messages.append({"role": "user", "content": tool_results})

        return {"reply": "Não consegui processar sua pergunta. Tente reformular."}

    except Exception as e:
        return {"reply": f"Erro no assistente: {str(e)}"}
