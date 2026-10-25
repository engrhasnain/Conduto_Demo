"use client";

import { ArrowRight, Calculator, Cloud, FileSearch, Layers, ShieldCheck, UserCheck } from "lucide-react";
import Link from "next/link";
import { useApp } from "@/components/providers";
import { Card, PageHeader } from "@/components/ui";
import type { Lang } from "@/lib/api";

type L3 = Record<Lang, string>;
const tx = (es: string, en: string, pt: string): L3 => ({ es, en, pt });

const C = {
  title: tx("Cómo lo hacemos", "How we do it", "Como fazemos"),
  sub: tx(
    "Las otras pantallas muestran qué hace el sistema con datos de ejemplo. Esta explica cómo lo construiríamos con los datos reales de Montamar: cómo funciona, las reglas que sigue, los pasos para ponerlo en marcha y las pocas cosas que necesitamos para empezar.",
    "The other screens show what the system does with example data. This one explains how we would build it with Montamar's real data: how it works, the rules it follows, the steps to put it into service, and the few things we need to start.",
    "As outras telas mostram o que o sistema faz com dados de exemplo. Esta explica como o construiríamos com os dados reais da Montamar: como funciona, as regras que segue, os passos para colocá-lo em operação e as poucas coisas que precisamos para começar.",
  ),
  flowTitle: tx("Arquitectura", "Architecture", "Arquitetura"),
  flow: [
    [tx("Fuentes", "Sources", "Fontes"), tx("Correo y adjuntos · carpetas compartidas · Excel y CSV · PDF y escaneos · Bejerman · plataformas de proveedores externos", "Email and attachments · shared folders · Excel and CSV · PDF and scans · Bejerman · external providers' platforms", "E-mail e anexos · pastas compartilhadas · Excel e CSV · PDF e digitalizações · Bejerman · plataformas de fornecedores externos")],
    [tx("Conectores y carga", "Connectors and loading", "Conectores e carga"), tx("Conectores de solo lectura traen los datos solos; reglas y un modelo entrenado llevan cada formato a la estructura común; una persona revisa y confirma", "Read-only connectors bring the data automatically; rules and a trained model bring each format into the common structure; a person reviews and confirms", "Conectores somente leitura trazem os dados sozinhos; regras e um modelo treinado levam cada formato para a estrutura comum; uma pessoa revisa e confirma")],
    [tx("Modelo común", "Common model", "Modelo comum"), tx("Proyectos, actividades, costos, avance, órdenes de cambio y eventos, con trazabilidad a la celda o página", "Projects, activities, costs, progress, change orders and events, traced to the cell or page", "Projetos, atividades, custos, avanço, ordens de alteração e ocorrências, rastreados até a célula ou página")],
    [tx("Indicadores", "Intelligence", "Indicadores"), tx("Valor ganado, margen pronosticado, alertas, benchmarks históricos", "Earned value, forecast margin, alerts, historical benchmarks", "Valor agregado, margem prevista, alertas, benchmarks históricos")],
    [tx("Uso", "Use", "Uso"), tx("Tablero, preguntas en lenguaje natural, y la carga de comprobantes aprobados en Bejerman", "Dashboard, natural-language questions, and posting approved documents into Bejerman", "Painel, perguntas em linguagem natural, e o lançamento de documentos aprovados no Bejerman")],
  ],
  principlesTitle: tx("Principios de diseño", "Design principles", "Princípios de projeto"),
  principles: [
    [Calculator, tx("Los números se calculan, no se adivinan", "Numbers are calculated, never guessed", "Os números são calculados, nunca adivinhados"), tx("Las cifras se calculan en la base de datos. La inteligencia artificial solo lee documentos, reconoce formatos y redacta respuestas; nunca inventa un número.", "Figures are computed in the database. Artificial intelligence only reads documents, recognizes formats and writes answers; it never invents a number.", "Os números são calculados no banco de dados. A inteligência artificial só lê documentos, reconhece formatos e redige respostas; nunca inventa um número.")],
    [FileSearch, tx("Todo número es trazable", "Every number is traceable", "Todo número é rastreável"), tx("Cada valor apunta a la celda, página o tarea del archivo original. La auditoría es un clic.", "Every value points to the cell, page or task of the original file. Auditing is one click.", "Cada valor aponta para a célula, página ou tarefa do arquivo original. Auditar é um clique.")],
    [Layers, tx("No reemplaza a Bejerman", "It does not replace Bejerman", "Não substitui o Bejerman"), tx("Bejerman sigue siendo el sistema contable y sigue conectado al estudio. Este sistema solo agrega los comprobantes que una persona aprobó: no modifica ni borra nada de lo ya cargado.", "Bejerman stays the accounting system and stays connected to the external accountant. This system only adds the documents a person approved: it never changes or deletes anything already posted.", "O Bejerman continua sendo o sistema contábil e continua conectado ao escritório. Este sistema só adiciona os documentos que uma pessoa aprovou: não altera nem apaga nada já lançado.")],
    [UserCheck, tx("Humano en el ciclo", "Human in the loop", "Humano no ciclo"), tx("Nada se importa sin revisión. Cada formato nuevo se aprende una vez y se reutiliza.", "Nothing is imported without review. Each new format is learned once and reused.", "Nada é importado sem revisão. Cada formato novo é aprendido uma vez e reutilizado.")],
    [Cloud, tx("En su nube", "In your cloud", "Na sua nuvem"), tx("Se instala en la nube de Montamar (por ejemplo, Microsoft Azure). Los datos no salen de su control.", "Installed in Montamar's own cloud account (for example, Microsoft Azure). Data stays under your control.", "Instalado na nuvem da própria Montamar (por exemplo, Microsoft Azure). Os dados ficam sob seu controle.")],
    [ShieldCheck, tx("Acceso de solo lectura", "Read-only access", "Acesso somente leitura"), tx("Las consultas a sistemas fuente y a la base consolidada son de solo lectura, con controles de tiempo y volumen.", "Queries to source systems and the consolidated store are read-only, with time and volume limits.", "As consultas aos sistemas fonte e à base consolidada são somente leitura, com limites de tempo e volume.")],
  ] as const,
  phasesTitle: tx("Hoja de ruta propuesta", "Proposed roadmap", "Roteiro proposto"),
  phases: [
    [tx("Fase 0 · Hoy", "Phase 0 · Today", "Fase 0 · Hoje"), tx("Demo", "Demo", "Demo"), tx("Esta demostración con datos sintéticos, para validar el caso de uso.", "This demo with synthetic data, to validate the use case.", "Esta demonstração com dados sintéticos, para validar o caso de uso.")],
    [tx("Fase 1 · 2–4 semanas", "Phase 1 · 2–4 weeks", "Fase 1 · 2–4 semanas"), tx("Diagnóstico", "Discovery", "Diagnóstico"), tx("Inventario de fuentes reales, 2–3 proyectos de muestra procesados, indicadores acordados con control de proyectos y finanzas.", "Inventory of real sources, 2–3 sample projects processed, indicators agreed with project controls and finance.", "Inventário das fontes reais, 2–3 projetos de amostra processados, indicadores acordados com controle de projetos e finanças.")],
    [tx("Fase 2 · 6–8 semanas", "Phase 2 · 6–8 weeks", "Fase 2 · 6–8 semanas"), tx("Piloto en una zona", "Pilot in one zone", "Piloto numa zona"), tx("Datos reales de una zona, conexion de solo lectura a Bejerman, tablero y preguntas en produccion para gerencia.", "Real data from one zone, read-only connection to Bejerman, dashboard and questions live for management.", "Dados reais de uma zona, conexao somente leitura ao Bejerman, painel e perguntas em producao para a gerencia.")],
    [tx("Fase 3", "Phase 3", "Fase 3"), tx("Escala al resto", "Roll out to the rest", "Escala para o resto"), tx("Las demás zonas, la lectura de archivos geoespaciales (SHP) y las mediciones de campo del mismo día.", "The remaining zones, reading geospatial files (SHP), and same-day field measurements.", "As demais zonas, a leitura de arquivos geoespaciais (SHP) e as medições de campo no mesmo dia.")],
  ],
  dataTitle: tx("Qué necesitamos para empezar", "What we need to start", "O que precisamos para começar"),
  dataIntro: tx(
    "Son pocas cosas, y casi todas son números. Con eso ya se puede calcular el ahorro con cifras de ustedes en vez de las nuestras.",
    "It is a short list, and most of it is numbers. With those we can work out the saving using your figures instead of ours.",
    "São poucas coisas, e quase todas são números. Com isso já dá para calcular a economia com números de vocês em vez dos nossos.",
  ),
  dataCols: [tx("Qué", "What", "O quê"), tx("Por qué lo necesitamos", "Why we need it", "Por que precisamos")],
  data: [
    [tx("Cuántas facturas de proveedores reciben por mes (o por día)",
        "How many supplier invoices you receive per month (or per day)",
        "Quantas faturas de fornecedores recebem por mês (ou por dia)"),
     tx("Es el número que multiplica todo lo demás. Sin él, cualquier ahorro que mostremos es el nuestro, no el de ustedes.",
        "It is the number everything else multiplies. Without it, any saving we show is ours, not yours.",
        "É o número que multiplica todo o resto. Sem ele, qualquer economia que mostremos é nossa, não de voces.")],
    [tx("Cuántos minutos lleva cargar una",
        "How many minutes it takes to enter one",
        "Quantos minutos leva lançar uma"),
     tx("Medido, no estimado: cronometren tres o cuatro. Es lo que convierte facturas en horas.",
        "Measured, not estimated: time three or four of them. It is what turns invoices into hours.",
        "Medido, não estimado: cronometrem três ou quatro. É o que transforma faturas em horas.")],
    [tx("Cuánto cuesta una hora de trabajo",
        "What an hour of that work costs",
        "Quanto custa uma hora desse trabalho"),
     tx("Para que el ahorro se pueda presentar en plata y no solo en tiempo. Un valor aproximado alcanza.",
        "So the saving can be put in money, not only in time. A rough figure is enough.",
        "Para que a economia possa ser apresentada em dinheiro, não só em tempo. Um valor aproximado basta.")],
    [tx("Un mes de facturas, como llegan hoy",
        "One month of invoices, exactly as they arrive today",
        "Um mês de faturas, como chegam hoje"),
     tx("Correo, escaneos y fotos incluidos, con los proveedores habituales. Es la unica forma de medir el porcentaje sobre sus documentos y no sobre los de la demostracion.",
        "Email, scans and photos included, from the usual suppliers. It is the only way to measure the percentage on your documents rather than on the demonstration's.",
        "E-mail, digitalizações e fotos incluídos, dos fornecedores habituais. É a única forma de medir a porcentagem nos documentos de vocês e não nos da demonstração.")],
    [tx("Si Bejerman tiene interfaz de importación",
        "Whether Bejerman has an import interface",
        "Se o Bejerman tem interface de importação"),
     tx("Es la única duda técnica que quedó abierta en la reunión. El sistema funciona de las dos maneras; saberlo solo decide cuál usamos.",
        "It is the one technical question left open in the meeting. The system works either way; knowing only decides which route we use.",
        "É a única dúvida técnica que ficou aberta na reunião. O sistema funciona das duas formas; saber apenas decide qual caminho usamos.")],
  ],
  connectorsLink: tx("Ver los conectores", "See the connectors", "Ver os conectores"),
  note: tx("Todos los datos de esta demo son sintéticos: proyectos, clientes y cifras son ficticios y fueron generados para ilustrar el método.", "All data in this demo is synthetic: projects, clients and figures are fictitious and were generated to illustrate the method.", "Todos os dados desta demo são sintéticos: projetos, clientes e números são fictícios e foram gerados para ilustrar o método."),
};

export default function MethodPage() {
  const { lang } = useApp();
  const L = (x: L3) => x[lang];
  return (
    <>
      <PageHeader title={L(C.title)} subtitle={L(C.sub)} />
      <div className="space-y-6">
        <Card title={L(C.flowTitle)} actions={<Link href="/connectors" className="inline-flex items-center gap-1 text-[13px] font-medium text-[#2a78d6] hover:underline">{L(C.connectorsLink)} <ArrowRight className="h-3.5 w-3.5" /></Link>}>
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

        <Card title={L(C.dataTitle)} subtitle={L(C.dataIntro)} bodyClass="px-0 pb-2">
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
