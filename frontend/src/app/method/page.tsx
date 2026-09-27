"use client";

import { ArrowRight, Calculator, Cloud, FileSearch, Layers, ShieldCheck, UserCheck } from "lucide-react";
import { useApp } from "@/components/providers";
import { Card, PageHeader } from "@/components/ui";
import type { Lang } from "@/lib/api";

type L3 = Record<Lang, string>;
const tx = (es: string, en: string, pt: string): L3 => ({ es, en, pt });

const C = {
  title: tx("Cómo lo hacemos", "How we do it", "Como fazemos"),
  sub: tx(
    "Las otras pantallas muestran qué hace el sistema con datos de ejemplo. Esta explica cómo lo construiríamos con los datos reales de Conduto: el problema, cómo funciona, las reglas que sigue, los pasos para ponerlo en marcha y qué necesitamos para empezar.",
    "The other screens show what the system does with example data. This one explains how we would build it with Conduto's real data: the problem, how it works, the rules it follows, the steps to put it into service and what we need to start.",
    "As outras telas mostram o que o sistema faz com dados de exemplo. Esta explica como o construiríamos com os dados reais da Conduto: o problema, como funciona, as regras que segue, os passos para colocá-lo em operação e o que precisamos para começar.",
  ),
  problemTitle: tx("El punto de partida", "Where we start", "O ponto de partida"),
  problems: [
    tx("El control de proyectos existe como proceso, pero vive en Excel y tablas dinámicas, con formatos distintos por país.", "Project control exists as a process, but lives in Excel and pivot tables, with different formats per country.", "O controle de projetos existe como processo, mas vive em Excel e tabelas dinâmicas, com formatos diferentes por país."),
    tx("Costos, cronogramas (Microsoft Project) y documentos (PDF) no están conectados: la rentabilidad se conoce tarde, al cierre.", "Costs, schedules (Microsoft Project) and documents (PDF) are not connected: profitability is known late, at close-out.", "Custos, cronogramas (Microsoft Project) e documentos (PDF) não estão conectados: a rentabilidade é conhecida tarde, no encerramento."),
    tx("La experiencia de proyectos cerrados no se puede consultar, así que no alimenta las nuevas ofertas.", "Experience from closed projects cannot be queried, so it does not feed new bids.", "A experiência de projetos encerrados não pode ser consultada, então não alimenta novas propostas."),
  ],
  flowTitle: tx("Arquitectura", "Architecture", "Arquitetura"),
  flow: [
    [tx("Fuentes", "Sources", "Fontes"), tx("Excel · Microsoft Project · PDF · Dynamics GP (hoy) · SAP o Dynamics 365 (mañana)", "Excel · Microsoft Project · PDF · Dynamics GP (today) · SAP or Dynamics 365 (tomorrow)", "Excel · Microsoft Project · PDF · Dynamics GP (hoje) · SAP ou Dynamics 365 (amanhã)")],
    [tx("Carga de datos", "Loading the data", "Carga de dados"), tx("Reglas y un modelo entrenado llevan cada formato a la estructura común; una persona revisa y confirma", "Rules and a trained model bring each format into the common structure; a person reviews and confirms", "Regras e um modelo treinado levam cada formato para a estrutura comum; uma pessoa revisa e confirma")],
    [tx("Modelo común", "Common model", "Modelo comum"), tx("Proyectos, actividades, costos, avance, órdenes de cambio y eventos, con trazabilidad a la celda o página", "Projects, activities, costs, progress, change orders and events, traced to the cell or page", "Projetos, atividades, custos, avanço, ordens de alteração e ocorrências, rastreados até a célula ou página")],
    [tx("Indicadores", "Intelligence", "Indicadores"), tx("Valor ganado, margen pronosticado, alertas, benchmarks históricos", "Earned value, forecast margin, alerts, historical benchmarks", "Valor agregado, margem prevista, alertas, benchmarks históricos")],
    [tx("Uso", "Use", "Uso"), tx("Tablero, preguntas en lenguaje natural, exportación a Power BI o al sistema contable", "Dashboard, natural-language questions, export to Power BI or the accounting system", "Painel, perguntas em linguagem natural, exportação para Power BI ou para o sistema contábil")],
  ],
  principlesTitle: tx("Principios de diseño", "Design principles", "Princípios de projeto"),
  principles: [
    [Calculator, tx("Los números se calculan, no se adivinan", "Numbers are calculated, never guessed", "Os números são calculados, nunca adivinhados"), tx("Las cifras se calculan en la base de datos. La inteligencia artificial solo lee documentos, reconoce formatos y redacta respuestas; nunca inventa un número.", "Figures are computed in the database. Artificial intelligence only reads documents, recognizes formats and writes answers; it never invents a number.", "Os números são calculados no banco de dados. A inteligência artificial só lê documentos, reconhece formatos e redige respostas; nunca inventa um número.")],
    [FileSearch, tx("Todo número es trazable", "Every number is traceable", "Todo número é rastreável"), tx("Cada valor apunta a la celda, página o tarea del archivo original. La auditoría es un clic.", "Every value points to the cell, page or task of the original file. Auditing is one click.", "Cada valor aponta para a célula, página ou tarefa do arquivo original. Auditar é um clique.")],
    [Layers, tx("Independiente del sistema contable", "Works with any accounting system", "Independente do sistema contábil"), tx("Funciona hoy sobre Dynamics GP y sobrevive a la migración a SAP o Dynamics 365. Los datos históricos limpios también ayudan a esa migración.", "Works today on top of Dynamics GP and survives the move to SAP or Dynamics 365. Clean historical data also helps that migration.", "Funciona hoje sobre o Dynamics GP e sobrevive à migração para SAP ou Dynamics 365. Dados históricos limpos também ajudam nessa migração.")],
    [UserCheck, tx("Humano en el ciclo", "Human in the loop", "Humano no ciclo"), tx("Nada se importa sin revisión. Cada formato nuevo se aprende una vez y se reutiliza.", "Nothing is imported without review. Each new format is learned once and reused.", "Nada é importado sem revisão. Cada formato novo é aprendido uma vez e reutilizado.")],
    [Cloud, tx("En su nube", "In your cloud", "Na sua nuvem"), tx("Se instala en la nube de Conduto (por ejemplo, Microsoft Azure). Los datos no salen de su control.", "Installed in Conduto's own cloud account (for example, Microsoft Azure). Data stays under your control.", "Instalado na nuvem da própria Conduto (por exemplo, Microsoft Azure). Os dados ficam sob seu controle.")],
    [ShieldCheck, tx("Acceso de solo lectura", "Read-only access", "Acesso somente leitura"), tx("Las consultas a sistemas fuente y a la base consolidada son de solo lectura, con controles de tiempo y volumen.", "Queries to source systems and the consolidated store are read-only, with time and volume limits.", "As consultas aos sistemas fonte e à base consolidada são somente leitura, com limites de tempo e volume.")],
  ] as const,
  phasesTitle: tx("Hoja de ruta propuesta", "Proposed roadmap", "Roteiro proposto"),
  phases: [
    [tx("Fase 0 · Hoy", "Phase 0 · Today", "Fase 0 · Hoje"), tx("Demo", "Demo", "Demo"), tx("Esta demostración con datos sintéticos, para validar el caso de uso.", "This demo with synthetic data, to validate the use case.", "Esta demonstração com dados sintéticos, para validar o caso de uso.")],
    [tx("Fase 1 · 2–4 semanas", "Phase 1 · 2–4 weeks", "Fase 1 · 2–4 semanas"), tx("Diagnóstico", "Discovery", "Diagnóstico"), tx("Inventario de fuentes reales, 2–3 proyectos de muestra procesados, indicadores acordados con control de proyectos y finanzas.", "Inventory of real sources, 2–3 sample projects processed, indicators agreed with project controls and finance.", "Inventário das fontes reais, 2–3 projetos de amostra processados, indicadores acordados com controle de projetos e finanças.")],
    [tx("Fase 2 · 6–8 semanas", "Phase 2 · 6–8 weeks", "Fase 2 · 6–8 semanas"), tx("Piloto Ecuador", "Ecuador pilot", "Piloto Equador"), tx("Datos reales de Ecuador, conexión de solo lectura a Dynamics GP, tablero y preguntas en producción para gerencia.", "Real Ecuador data, read-only connection to Dynamics GP, dashboard and questions live for management.", "Dados reais do Equador, conexão somente leitura ao Dynamics GP, painel e perguntas em produção para a gerência.")],
    [tx("Fase 3", "Phase 3", "Fase 3"), tx("Escala al grupo", "Group rollout", "Escala para o grupo"), tx("Perú y Brasil, plantillas por país y conexión al nuevo sistema contable (SAP o Dynamics 365).", "Peru and Brazil, per-country templates and a connection to the new accounting system (SAP or Dynamics 365).", "Peru e Brasil, modelos por país e conexão ao novo sistema contábil (SAP ou Dynamics 365).")],
  ],
  dataTitle: tx("Qué necesitamos para el diagnóstico", "What we need for discovery", "O que precisamos para o diagnóstico"),
  dataCols: [tx("Fuente", "Source", "Fonte"), tx("Mínimo", "Minimum", "Mínimo"), tx("Ideal", "Ideal", "Ideal")],
  data: [
    [tx("Control de costos (Excel)", "Cost control (Excel)", "Controle de custos (Excel)"), tx("2–3 proyectos: al menos uno cerrado y uno activo", "2–3 projects: at least one closed and one active", "2–3 projetos: ao menos um encerrado e um ativo"), tx("Todos los proyectos de los últimos 5 años", "All projects from the last 5 years", "Todos os projetos dos últimos 5 anos")],
    [tx("Cronogramas (Microsoft Project)", "Schedules (Microsoft Project)", "Cronogramas (Microsoft Project)"), tx("Los archivos de cronograma de esos proyectos", "The schedule files for those projects", "Os arquivos de cronograma desses projetos"), tx("Línea base y actualizaciones mensuales", "Baseline and monthly updates", "Linha de base e atualizações mensais")],
    [tx("Contratos y órdenes de cambio (PDF)", "Contracts and change orders (PDF)", "Contratos e ordens de alteração (PDF)"), tx("Contrato y órdenes de cambio de los proyectos de muestra", "Contract and change orders for the sample projects", "Contrato e ordens de alteração dos projetos de amostra"), tx("Historial completo de órdenes de cambio y reclamos", "Full history of change orders and claims", "Histórico completo de ordens de alteração e pleitos")],
    [tx("Informes mensuales", "Monthly reports", "Relatórios mensais"), tx("Últimos 6 informes de un proyecto activo", "Last 6 reports of an active project", "Últimos 6 relatórios de um projeto ativo"), tx("Todos los informes e informes de cierre", "All reports and close-out reports", "Todos os relatórios e relatórios de encerramento")],
    [tx("Dynamics GP", "Dynamics GP", "Dynamics GP"), tx("Exportación del libro mayor por proyecto (Excel o texto)", "General-ledger export by project (Excel or text file)", "Exportação do razão por projeto (Excel ou arquivo de texto)"), tx("Acceso de solo lectura a la base de datos contable", "Read-only access to the accounting database", "Acesso somente leitura ao banco de dados contábil")],
    [tx("Personas", "People", "Pessoas"), tx("2 horas con control de proyectos, 1 hora con tecnología, 1 hora con finanzas", "2 hours with project controls, 1 hour with technology, 1 hour with finance", "2 horas com controle de projetos, 1 hora com tecnologia, 1 hora com finanças"), tx("Un responsable de datos por país", "One data owner per country", "Um responsável de dados por país")],
  ],
  note: tx("Todos los datos de esta demo son sintéticos: proyectos, clientes y cifras son ficticios y fueron generados para ilustrar el método.", "All data in this demo is synthetic: projects, clients and figures are fictitious and were generated to illustrate the method.", "Todos os dados desta demo são sintéticos: projetos, clientes e números são fictícios e foram gerados para ilustrar o método."),
};

export default function MethodPage() {
  const { lang } = useApp();
  const L = (x: L3) => x[lang];
  return (
    <>
      <PageHeader title={L(C.title)} subtitle={L(C.sub)} />
      <div className="space-y-6">
        <Card title={L(C.problemTitle)}>
          <ul className="grid gap-3 md:grid-cols-3">
            {C.problems.map((p, i) => <li key={i} className="rounded-lg bg-slate-50 p-4 text-[13.5px] leading-relaxed text-slate-700 ring-1 ring-slate-100">{L(p)}</li>)}
          </ul>
        </Card>

        <Card title={L(C.flowTitle)}>
          <div className="flex flex-col gap-2 xl:flex-row xl:items-stretch">
            {C.flow.map(([h, d], i) => (
              <div key={i} className="flex flex-1 items-center gap-2">
                <div className="h-full flex-1 rounded-xl bg-[#132a45] p-4 text-white">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-sky-300">{i + 1}</p>
                  <p className="mt-1 text-[14px] font-semibold">{L(h)}</p>
                  <p className="mt-1 text-[12.5px] leading-relaxed text-slate-300">{L(d)}</p>
                </div>
                {i < C.flow.length - 1 && <ArrowRight className="hidden h-4 w-4 shrink-0 text-slate-400 xl:block" />}
              </div>
            ))}
          </div>
        </Card>

        <Card title={L(C.principlesTitle)}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {C.principles.map(([Icon, h, d], i) => (
              <div key={i} className="flex gap-3">
                <div className="h-fit rounded-lg bg-blue-50 p-2 text-[#1c5cab]"><Icon className="h-4 w-4" /></div>
                <div><p className="text-[14px] font-semibold text-slate-900">{L(h)}</p><p className="mt-0.5 text-[13px] leading-relaxed text-slate-600">{L(d)}</p></div>
              </div>
            ))}
          </div>
        </Card>

        <Card title={L(C.phasesTitle)}>
          <ol className="grid gap-3 md:grid-cols-4">
            {C.phases.map(([when, what, d], i) => (
              <li key={i} className={`rounded-xl p-4 ring-1 ${i === 0 ? "bg-amber-50 ring-amber-200" : "bg-white ring-slate-200"}`}>
                <p className="text-[11.5px] font-semibold uppercase tracking-wide text-slate-500">{L(when)}</p>
                <p className="mt-1 text-[15px] font-semibold text-slate-900">{L(what)}</p>
                <p className="mt-1 text-[13px] leading-relaxed text-slate-600">{L(d)}</p>
              </li>
            ))}
          </ol>
        </Card>

        <Card title={L(C.dataTitle)} bodyClass="px-0 pb-2">
          <table className="min-w-full text-[13px]">
            <thead className="border-y border-slate-100 bg-slate-50/60">
              <tr>{C.dataCols.map((c, i) => <th key={i} className="px-5 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-slate-500">{L(c)}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {C.data.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className={`px-5 py-2.5 ${j === 0 ? "font-medium text-slate-900" : "text-slate-600"}`}>{L(c)}</td>)}</tr>)}
            </tbody>
          </table>
        </Card>

        <p className="text-[12.5px] text-slate-500">{L(C.note)}</p>
      </div>
    </>
  );
}
