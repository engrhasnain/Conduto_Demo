"""Source documents in the local language: contracts, change orders, monthly and
close-out reports (PDF) and MS Project schedules (MSPDI XML)."""
from xml.sax.saxutils import escape

from ..config import STATUS_PERIOD
from ..fmt import fmt_date, fmt_money, fmt_number, fmt_pct
from ..i18n import CO_CAUSES, ISSUE_CATEGORIES, pick
from ..utils import add_months, first_day, last_day
from .pdf_writer import PdfDoc
from .simulate import SimResult
from .specs import GENERIC_LESSONS
from .templates import TEMPLATES

MONTH_FULL = {
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "pt": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
}


def month_full(period: str, lang: str) -> str:
    return f"{MONTH_FULL[lang][int(period[5:]) - 1]} {period[:4]}"


T = {
    "es": dict(
        contract_title="CONTRATO DE CONSTRUCCIÓN N° {code}-C", contract_label="Contrato de construcción",
        k_client="Contratante", k_contractor="Contratista", k_project="Proyecto", k_location="Ubicación",
        k_type="Modalidad", k_value="Monto del contrato", k_term="Plazo de ejecución", k_start="Fecha de inicio",
        k_advance="Anticipo", k_retention="Retención de garantía",
        lump_sum="Suma alzada (precio global)", unit_price="Precios unitarios",
        term="{P} meses calendario", advance="10% del monto del contrato", retention="5% de cada planilla de avance",
        contractor="CONDUTO (entidad de demostración)",
        clauses_p1=[
            "PRIMERA – OBJETO. {description}",
            "SEGUNDA – ALCANCE. {scope}",
            "TERCERA – FORMA DE PAGO. Planillas mensuales según el avance físico certificado por la fiscalización, con retención de garantía del 5%.",
            "CUARTA – ÓRDENES DE CAMBIO. Todo trabajo adicional o modificación de alcance requerirá una orden de cambio aprobada por escrito por el Contratante antes de su ejecución. Los trabajos ejecutados sin orden aprobada no generarán derecho de pago, salvo acuerdo posterior entre las partes.",
            "QUINTA – MULTAS. Por cada día de retraso imputable al Contratista se aplicará una multa del 0,1% del monto del contrato, con un tope del 10%.",
        ],
        clauses_p2=[
            "SEXTA – FUERZA MAYOR. Las paralizaciones por fuerza mayor debidamente comprobadas ampliarán el plazo, sin reconocimiento de costos de standby salvo acuerdo expreso.",
            "SÉPTIMA – RELACIONAMIENTO COMUNITARIO. El Contratante es responsable de los acuerdos con las comunidades del área de influencia. Los paros comunitarios no imputables al Contratista darán derecho a ampliación de plazo y a la presentación de reclamos por standby.",
            "OCTAVA – CONTROVERSIAS. Las controversias se resolverán mediante negociación directa y, en su defecto, mediante arbitraje.",
        ],
        scope_pipeline="El Contratista ejecutará la construcción, montaje, pruebas y puesta en servicio. La tubería y las válvulas principales serán suministradas por el Contratante.",
        scope_civil="El Contratista suministrará los materiales de obra civil y ejecutará el montaje. Los equipos mayores serán suministrados por el Contratante.",
        sign_client="Por el Contratante", sign_contractor="Por el Contratista",
        co_title="ORDEN DE CAMBIO N° {number}", co_label="Orden de cambio",
        k_contract="Contrato", k_date="Fecha de presentación", k_activity="Actividad afectada", k_cause="Causa",
        k_amount="Monto solicitado", k_impact="Impacto en plazo", k_status="Estado", k_decision="Fecha de resolución",
        days="{d} días", status=dict(approved="Aprobada", pending="Pendiente de aprobación", rejected="Rechazada"),
        description="Descripción", justification="Justificación",
        just=dict(
            client_request="El Cliente solicitó el trabajo adicional mediante comunicación escrita. El alcance no forma parte del contrato original.",
            design="La ingeniería de detalle emitida por el Cliente modificó la ubicación y el alcance de los trabajos.",
            geotech="Las condiciones encontradas en campo difieren de los estudios geotécnicos entregados por el Cliente.",
            community="La paralización no fue imputable al Contratista, conforme a la cláusula séptima del contrato.",
            permits="El retraso en la emisión de permisos es responsabilidad del Cliente y extendió la permanencia en obra.",
            scope="Ampliación de alcance solicitada por el Cliente.",
            weather="Precipitaciones superiores al promedio histórico de los últimos 10 años.",
            escalation="Variación del índice de precios de materiales superior al 10% desde la fecha de la oferta.",
        ),
        executed_note="Nota: los trabajos fueron ejecutados en campo por instrucción de la fiscalización, a la espera de la aprobación formal de esta orden de cambio.",
        rejected_note="Resolución: el Cliente rechazó la orden por considerar que el riesgo estaba incluido en el precio global del contrato.",
        report_title="INFORME MENSUAL DE AVANCE – {month}", report_label="Informe mensual de avance",
        k_period="Periodo", k_manager="Gerente de proyecto",
        h_progress="1. Avance físico", h_production="2. Producción", h_cost="3. Costos",
        h_events="4. Eventos del periodo", h_cos="5. Órdenes de cambio", h_actions="6. Acciones y próximos pasos",
        progress_line="Avance programado acumulado: {planned}. Avance real acumulado: {actual}.",
        production_line="Kilómetros soldados acumulados: {km} de {L} km. Juntas soldadas acumuladas: {welds}. Tasa de reparación del periodo: {rate}.",
        cost_line="Costo real del periodo: {month}. Costo real acumulado: {cum}.",
        no_events="Sin eventos relevantes en el periodo.",
        event_line="{cat}: {text} Días perdidos: {days}. Impacto estimado: {cost}.",
        co_line="{number} – {title}. Monto: {amount}. Estado: {status}.",
        pending_header="Órdenes de cambio pendientes de aprobación al cierre del periodo:",
        pending_line="{number} – {title}. Monto: {amount}. Presentada el {date} ({days} días sin resolución).",
        no_cos="Sin órdenes de cambio en el periodo.",
        actions=dict(
            weather="Reprogramar frentes de bajado y tapado a tramos con mejor drenaje y evaluar reclamo por standby.",
            community="Reforzar el plan de relacionamiento comunitario y documentar el standby para su reclamo.",
            permits="Seguimiento semanal con el Cliente para la emisión de permisos pendientes.",
            geotech="Emitir orden de cambio por las condiciones geotécnicas encontradas.",
            quality="Recalificación de soldadores y aumento de la inspección radiográfica al 100% durante dos semanas.",
            supply="Activar proveedor alterno y acelerar la entrega de materiales críticos.",
            equipment="Mantener equipo de respaldo en sitio para cruces especiales.",
            force_majeure="Mantener personal mínimo y documentar costos fijos para posible compensación.",
        ),
        default_action="Mantener el ritmo de producción y el control semanal de costos.",
        final_title="INFORME DE CIERRE DE PROYECTO", final_label="Informe de cierre",
        k_planned_term="Plazo programado", k_actual_term="Plazo real", k_final_contract="Monto contractual final",
        k_final_cost="Costo final", k_bid_margin="Margen de oferta", k_final_margin="Margen final",
        months="{n} meses", h_main_events="Eventos principales", h_lessons="Lecciones aprendidas",
        pipe_note="Tubería suministrada por el Contratante",
    ),
    "pt": dict(
        contract_title="CONTRATO DE CONSTRUÇÃO Nº {code}-C", contract_label="Contrato de construção",
        k_client="Contratante", k_contractor="Contratada", k_project="Projeto", k_location="Localização",
        k_type="Modalidade", k_value="Valor do contrato", k_term="Prazo de execução", k_start="Data de início",
        k_advance="Adiantamento", k_retention="Retenção de garantia",
        lump_sum="Preço global (empreitada)", unit_price="Preços unitários",
        term="{P} meses corridos", advance="10% do valor do contrato", retention="5% de cada medição",
        contractor="CONDUTO (entidade de demonstração)",
        clauses_p1=[
            "CLÁUSULA PRIMEIRA – OBJETO. {description}",
            "CLÁUSULA SEGUNDA – ESCOPO. {scope}",
            "CLÁUSULA TERCEIRA – PAGAMENTO. Medições mensais conforme o avanço físico atestado pela fiscalização, com retenção de garantia de 5%.",
            "CLÁUSULA QUARTA – ORDENS DE ALTERAÇÃO. Todo serviço adicional ou mudança de escopo exigirá ordem de alteração aprovada por escrito pela Contratante antes de sua execução. Serviços executados sem ordem aprovada não gerarão direito a pagamento, salvo acordo posterior entre as partes.",
            "CLÁUSULA QUINTA – MULTAS. Por dia de atraso imputável à Contratada será aplicada multa de 0,1% do valor do contrato, limitada a 10%.",
        ],
        clauses_p2=[
            "CLÁUSULA SEXTA – FORÇA MAIOR. Paralisações por força maior devidamente comprovadas prorrogarão o prazo, sem reconhecimento de custos de standby salvo acordo expresso.",
            "CLÁUSULA SÉTIMA – RELACIONAMENTO COMUNITÁRIO. A Contratante é responsável pelos acordos com as comunidades da área de influência. Paralisações comunitárias não imputáveis à Contratada darão direito à prorrogação de prazo e a pleitos de standby.",
            "CLÁUSULA OITAVA – CONTROVÉRSIAS. As controvérsias serão resolvidas por negociação direta e, na falta de acordo, por arbitragem.",
        ],
        scope_pipeline="A Contratada executará a construção, montagem, testes e comissionamento. Os tubos e as válvulas principais serão fornecidos pela Contratante.",
        scope_civil="A Contratada fornecerá os materiais de obra civil e executará a montagem. Os equipamentos principais serão fornecidos pela Contratante.",
        sign_client="Pela Contratante", sign_contractor="Pela Contratada",
        co_title="ORDEM DE ALTERAÇÃO Nº {number}", co_label="Ordem de alteração",
        k_contract="Contrato", k_date="Data de apresentação", k_activity="Atividade afetada", k_cause="Causa",
        k_amount="Valor solicitado", k_impact="Impacto no prazo", k_status="Situação", k_decision="Data da decisão",
        days="{d} dias", status=dict(approved="Aprovada", pending="Pendente de aprovação", rejected="Rejeitada"),
        description="Descrição", justification="Justificativa",
        just=dict(
            client_request="A Contratante solicitou o serviço adicional por comunicação escrita. O escopo não faz parte do contrato original.",
            design="A engenharia de detalhamento emitida pela Contratante alterou a localização e o escopo dos serviços.",
            geotech="As condições encontradas em campo diferem dos estudos geotécnicos entregues pela Contratante.",
            community="A paralisação não foi imputável à Contratada, conforme a cláusula sétima do contrato.",
            permits="O atraso na emissão das licenças é de responsabilidade da Contratante e estendeu a permanência em obra.",
            scope="Ampliação de escopo solicitada pela Contratante.",
            weather="Precipitações acima da média histórica dos últimos 10 anos.",
            escalation="Variação do índice de preços de materiais superior a 10% desde a data da proposta.",
        ),
        executed_note="Nota: os serviços foram executados em campo por instrução da fiscalização, aguardando a aprovação formal desta ordem de alteração.",
        rejected_note="Decisão: a Contratante rejeitou a ordem por considerar o risco incluído no preço global do contrato.",
        report_title="RELATÓRIO MENSAL DE AVANÇO – {month}", report_label="Relatório mensal de avanço",
        k_period="Período", k_manager="Gerente do projeto",
        h_progress="1. Avanço físico", h_production="2. Produção", h_cost="3. Custos",
        h_events="4. Ocorrências do período", h_cos="5. Ordens de alteração", h_actions="6. Ações e próximos passos",
        progress_line="Avanço previsto acumulado: {planned}. Avanço realizado acumulado: {actual}.",
        production_line="Quilômetros soldados acumulados: {km} de {L} km. Juntas soldadas acumuladas: {welds}. Taxa de reparo do período: {rate}.",
        cost_line="Custo realizado no período: {month}. Custo realizado acumulado: {cum}.",
        no_events="Sem ocorrências relevantes no período.",
        event_line="{cat}: {text} Dias perdidos: {days}. Impacto estimado: {cost}.",
        co_line="{number} – {title}. Valor: {amount}. Situação: {status}.",
        pending_header="Ordens de alteração pendentes de aprovação no fechamento do período:",
        pending_line="{number} – {title}. Valor: {amount}. Apresentada em {date} ({days} dias sem decisão).",
        no_cos="Sem ordens de alteração no período.",
        actions=dict(
            weather="Reprogramar as frentes de abaixamento e cobertura para trechos com melhor drenagem e avaliar pleito de standby.",
            community="Reforçar o plano de relacionamento comunitário e documentar o standby para pleito.",
            permits="Acompanhamento semanal com a Contratante para emissão das licenças pendentes.",
            geotech="Emitir ordem de alteração pelas condições geotécnicas encontradas.",
            quality="Requalificação dos soldadores e inspeção radiográfica de 100% por duas semanas.",
            supply="Ativar fornecedor alternativo e acelerar a entrega de materiais críticos.",
            equipment="Manter equipamento reserva no canteiro para travessias especiais.",
            force_majeure="Manter equipe mínima e documentar custos fixos para possível compensação.",
        ),
        default_action="Manter o ritmo de produção e o controle semanal de custos.",
        final_title="RELATÓRIO DE ENCERRAMENTO DO PROJETO", final_label="Relatório de encerramento",
        k_planned_term="Prazo previsto", k_actual_term="Prazo real", k_final_contract="Valor contratual final",
        k_final_cost="Custo final", k_bid_margin="Margem da proposta", k_final_margin="Margem final",
        months="{n} meses", h_main_events="Principais ocorrências", h_lessons="Lições aprendidas",
        pipe_note="Tubos fornecidos pela Contratante",
    ),
}


def write_contract(sim: SimResult, path) -> tuple[list[str], str]:
    L, lang, s = T[sim.lang], sim.lang, sim.spec
    doc = PdfDoc(path, lang, L["contract_label"])
    doc.title(L["contract_title"].format(code=s["code"]))
    li = 0 if lang == "es" else 2
    doc.kv([
        (L["k_client"], s["client"]),
        (L["k_contractor"], L["contractor"]),
        (L["k_project"], f"{s['code']} – {s['name']}"),
        (L["k_location"], s["region"]),
        (L["k_type"], L[s["contract_type"]]),
        (L["k_value"], fmt_money(sim.contract, sim.currency, lang)),
        (L["k_term"], L["term"].format(P=sim.P)),
        (L["k_start"], fmt_date(first_day(s["start"]), lang)),
        (L["k_advance"], L["advance"]),
        (L["k_retention"], L["retention"]),
    ])
    scope = L["scope_pipeline"] if s["kind"] == "pipeline" else L["scope_civil"]
    for cl in L["clauses_p1"]:
        doc.para(cl.format(description=s["description"][li], scope=scope))
    doc.new_page()
    for cl in L["clauses_p2"]:
        doc.para(cl)
    doc.signatures(L["sign_client"], L["sign_contractor"])
    return doc.save(), "p.1"


def write_change_order(sim: SimResult, co: dict, path) -> tuple[list[str], str]:
    L, lang, s = T[sim.lang], sim.lang, sim.spec
    li = 0 if lang == "es" else 2
    doc = PdfDoc(path, lang, f"{L['co_label']} {co['number']}")
    doc.title(L["co_title"].format(number=co["number"]))
    tpl = TEMPLATES[s["country"]]
    rows = [
        (L["k_project"], f"{s['code']} – {s['name']}"),
        (L["k_contract"], f"{s['code']}-C"),
        (L["k_client"], s["client"]),
        (L["k_date"], fmt_date(co["submitted_date"], lang)),
        (L["k_activity"], tpl["labels"][co["activity"]]),
        (L["k_cause"], pick(CO_CAUSES[co["cause"]], lang)),
        (L["k_amount"], fmt_money(co["amount"], sim.currency, lang)),
        (L["k_impact"], L["days"].format(d=co["schedule_impact_days"])),
        (L["k_status"], L["status"][co["status"]]),
    ]
    if co["decision_date"]:
        rows.append((L["k_decision"], fmt_date(co["decision_date"], lang)))
    doc.kv(rows)
    doc.heading(L["description"])
    doc.para(co["titles"][li] + ".")
    doc.heading(L["justification"])
    doc.para(L["just"][co["cause"]])
    if co["status"] == "pending" and co["executed"] > 0:
        doc.para(L["executed_note"], bold=True)
    if co["status"] == "rejected":
        doc.para(L["rejected_note"], bold=True)
    doc.signatures(L["sign_contractor"], L["sign_client"])
    return doc.save(), "p.1"


def _days_between(d1: str, period_end: str) -> int:
    from datetime import date
    a = date.fromisoformat(d1)
    b = date.fromisoformat(period_end)
    return (b - a).days


def write_monthly_report(sim: SimResult, t: int, path, stale: bool = False) -> tuple[list[str], dict]:
    """Returns page texts and {issue_index: 'p.N'} for issues reported this month.

    stale=True reproduces a common real-world error: the cumulative cost is copied
    from the previous month's report instead of the cost-control workbook."""
    L, lang, s = T[sim.lang], sim.lang, sim.spec
    li = 0 if lang == "es" else 2
    period = sim.periods[t]
    doc = PdfDoc(path, lang, f"{L['report_label']} {period}")
    doc.title(L["report_title"].format(month=month_full(period, lang).upper()))
    doc.kv([
        (L["k_project"], f"{s['code']} – {s['name']}"),
        (L["k_client"], s["client"]),
        (L["k_period"], month_full(period, lang)),
        (L["k_manager"], s["manager"]),
    ])
    bac = sum(sim.bac.values())
    planned = sum(sim.planned[a][t] * sim.bac[a] for a in sim.bac) / bac
    actual = sum(sim.actual[a][t] * sim.bac[a] for a in sim.bac) / bac
    doc.heading(L["h_progress"])
    doc.para(L["progress_line"].format(planned=fmt_pct(planned, lang), actual=fmt_pct(actual, lang)))
    if sim.production:
        prod = sim.production[t]
        prev = sim.production[t - 1] if t > 0 else {"welds": 0, "repairs": 0}
        new_welds = prod["welds"] - prev["welds"]
        rate = (prod["repairs"] - prev["repairs"]) / new_welds if new_welds > 0 else 0.0
        doc.heading(L["h_production"])
        doc.para(L["production_line"].format(
            km=fmt_number(prod["km"], lang, 1), L=fmt_number(s["length"], lang, 0),
            welds=fmt_number(prod["welds"], lang, 0), rate=fmt_pct(rate, lang)))
    month_cost = sum(sim.costs[a][ct][t] for a in sim.costs for ct in sim.costs[a])
    cum_cost = sum(sum(sim.costs[a][ct][: t + (0 if stale else 1)]) for a in sim.costs for ct in sim.costs[a])
    doc.heading(L["h_cost"])
    doc.para(L["cost_line"].format(month=fmt_money(month_cost, sim.currency, lang, 0), cum=fmt_money(cum_cost, sim.currency, lang, 0)))

    doc.heading(L["h_events"])
    issue_pages = {}
    month_issues = [(i, x) for i, x in enumerate(sim.issues) if x["period"] == period]
    for i, x in month_issues:
        issue_pages[i] = f"p.{doc.bullet(L['event_line'].format(cat=pick(ISSUE_CATEGORIES[x['category']], lang), text=x['texts'][li], days=x['days'], cost=fmt_money(x['cost'], sim.currency, lang, 0)))}"
    if not month_issues:
        doc.para(L["no_events"])

    doc.heading(L["h_cos"])
    month_cos = [c for c in sim.cos if c["period"] == period]
    for c in month_cos:
        doc.bullet(L["co_line"].format(number=c["number"], title=c["titles"][li], amount=fmt_money(c["amount"], sim.currency, lang, 0), status=L["status"][c["status"]]))
    period_end = last_day(period)
    pending = [c for c in sim.cos if c["status"] == "pending" and c["submitted_date"] <= period_end]
    if pending:
        doc.para(L["pending_header"], bold=True)
        for c in pending:
            doc.bullet(L["pending_line"].format(number=c["number"], title=c["titles"][li], amount=fmt_money(c["amount"], sim.currency, lang, 0),
                                                date=fmt_date(c["submitted_date"], lang), days=_days_between(c["submitted_date"], period_end)))
    if not month_cos and not pending:
        doc.para(L["no_cos"])

    doc.heading(L["h_actions"])
    cats = {x["category"] for _, x in month_issues}
    for cat in sorted(cats):
        doc.bullet(L["actions"][cat])
    if not cats:
        doc.bullet(L["default_action"])
    return doc.save(), issue_pages


def write_final_report(sim: SimResult, path, final_cost: float, revised: float) -> list[str]:
    L, lang, s = T[sim.lang], sim.lang, sim.spec
    li = 0 if lang == "es" else 2
    doc = PdfDoc(path, lang, L["final_label"])
    doc.title(L["final_title"])
    doc.kv([
        (L["k_project"], f"{s['code']} – {s['name']}"),
        (L["k_client"], s["client"]),
        (L["k_planned_term"], L["months"].format(n=sim.P)),
        (L["k_actual_term"], L["months"].format(n=sim.A)),
        (L["k_value"], fmt_money(sim.contract, sim.currency, lang, 0)),
        (L["k_final_contract"], fmt_money(revised, sim.currency, lang, 0)),
        (L["k_final_cost"], fmt_money(final_cost, sim.currency, lang, 0)),
        (L["k_bid_margin"], fmt_pct(sim.bid_margin, lang)),
        (L["k_final_margin"], fmt_pct((revised - final_cost) / revised, lang)),
    ])
    doc.heading(L["h_main_events"])
    if sim.issues:
        for x in sim.issues:
            doc.bullet(f"{month_full(x['period'], lang)} – {pick(ISSUE_CATEGORIES[x['category']], lang)}: {x['texts'][li]}")
    else:
        doc.para(L["no_events"])
    doc.heading(L["h_lessons"])
    for key in s.get("lessons", []):
        doc.bullet(GENERIC_LESSONS[key][li])
    return doc.save()


def write_schedule_xml(sim: SimResult, path, status_period: str | None = None, name_override=None) -> dict:
    """MS Project XML (MSPDI). Returns {uid: 'Task UID n'}."""
    s = sim.spec
    tpl = TEMPLATES[s["country"]]
    status = status_period or (sim.periods[-1] if sim.closed else STATUS_PERIOD)
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Project xmlns="http://schemas.microsoft.com/project">',
        "  <SaveVersion>14</SaveVersion>",
        f"  <Name>{escape(s['code'])}.xml</Name>",
        f"  <Title>{escape(name_override or s['code'] + ' ' + s['name'])}</Title>",
        f"  <StartDate>{first_day(s['start'])}T08:00:00</StartDate>",
        f"  <FinishDate>{last_day(sim.forecast_finish)}T17:00:00</FinishDate>",
        f"  <StatusDate>{last_day(status)}T17:00:00</StatusDate>",
        f"  <CurrencyCode>{sim.currency}</CurrencyCode>",
        "  <Tasks>",
        "    <Task><UID>0</UID><ID>0</ID>"
        f"<Name>{escape(s['name'])}</Name><OutlineLevel>0</OutlineLevel><Summary>1</Summary></Task>",
    ]
    locs = {}
    for task in sim.tasks:
        pct = int(round(task["pct"] * 100))
        actual = f"<ActualStart>{task['start']}T08:00:00</ActualStart>" if pct > 0 else ""
        if pct >= 100:
            actual += f"<ActualFinish>{task['finish']}T17:00:00</ActualFinish>"
        lines.append(
            f"    <Task><UID>{task['uid']}</UID><ID>{task['uid']}</ID><Name>{escape(tpl['labels'][task['activity']])}</Name>"
            f"<WBS>{task['uid']}</WBS><OutlineLevel>1</OutlineLevel>"
            f"<Start>{task['start']}T08:00:00</Start><Finish>{task['finish']}T17:00:00</Finish>{actual}"
            f"<PercentComplete>{pct}</PercentComplete>"
            f"<Baseline><Number>0</Number><Start>{task['baseline_start']}T08:00:00</Start><Finish>{task['baseline_finish']}T17:00:00</Finish></Baseline>"
            "</Task>"
        )
        locs[task["uid"]] = f"Task UID {task['uid']}"
    lines += ["  </Tasks>", "</Project>", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return locs
