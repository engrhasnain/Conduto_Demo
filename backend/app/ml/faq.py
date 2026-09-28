"""Built-in knowledge base for general questions: project-control concepts, how the
system works, and small talk. Retrieved with a TF-IDF similarity model, so the
assistant can answer "what is a change order?" or "is this real data?" offline."""

from ..services.ingestion.normalize import norm

MIN_SCORE = 0.42

# Question words carry no topic: without removing them "what is the weather" matches "what is the margin".
QUESTION_WORDS = set("""
que qué es son el la los las un una de del en por para con como cómo cual cuál cuales cuáles significa significan explicame explícame
define definir dime puedes me te se mi tu su y o a al lo le
what is are the a an of to in on for does do mean means meaning explain define tell me you your i my how and or can
o os as um uma é e da do das dos no na nos nas pra para com como qual quais significa explique defina me diz você
""".split())


def content(text: str) -> str:
    toks = [t for t in norm(text).split() if t not in QUESTION_WORDS]
    return " ".join(toks) or norm(text)

FAQ = [
    # ---------------- concepts
    dict(id="margin", q=["qué es el margen", "margen ofertado", "margen pronosticado", "what is the margin", "bid margin", "forecast margin", "o que é a margem", "margem prevista", "margen", "margin", "margem"],
         a=("El **margen** es la diferencia entre lo que el cliente paga (el contrato) y lo que cuesta hacer la obra, expresada como porcentaje del contrato. El **margen ofertado** es el que se calculó al presentar la oferta; el **margen pronosticado** es el que se espera al terminar, según los costos reales hasta hoy.",
            "The **margin** is the difference between what the client pays (the contract) and what the work costs, as a percentage of the contract. The **bid margin** is what was calculated when bidding; the **forecast margin** is what we expect at the end, based on actual costs so far.",
            "A **margem** é a diferença entre o que o cliente paga (o contrato) e o que custa executar a obra, em porcentagem do contrato. A **margem ofertada** é a calculada na proposta; a **margem prevista** é a esperada no final, com base nos custos reais até hoje.")),
    dict(id="change_order", q=["qué es una orden de cambio", "orden de cambio", "órdenes de cambio", "adicionales", "what is a change order", "change order", "change orders", "o que é uma ordem de alteração", "ordem de alteração", "aditivo"],
         a=("Una **orden de cambio** es un documento que modifica el contrato: trabajo adicional, un cambio de diseño o un reclamo (por ejemplo, por paralización). Mientras está **pendiente**, el costo ya puede haberse gastado pero el cliente todavía no lo paga, y eso reduce el margen.",
            "A **change order** is a document that modifies the contract: extra work, a design change or a claim (for example, for a work stoppage). While it is **pending**, the cost may already be spent but the client has not agreed to pay it yet, which reduces the margin.",
            "Uma **ordem de alteração** é um documento que modifica o contrato: serviço adicional, mudança de projeto ou um pleito (por exemplo, por paralisação). Enquanto está **pendente**, o custo pode já ter sido gasto mas o cliente ainda não aceitou pagá-lo, o que reduz a margem.")),
    dict(id="earned_value", q=["qué es el valor ganado", "valor ganado", "gestión del valor ganado", "what is earned value", "earned value", "earned value management", "o que é valor agregado", "valor agregado", "evm"],
         a=("El **valor ganado** es el trabajo realmente hecho, valorizado con el presupuesto. Si un proyecto de 100 va al 40% de avance, su valor ganado es 40, aunque se hayan gastado 50. Comparar valor ganado con lo gastado y con lo planificado muestra si el proyecto va caro o atrasado.",
            "**Earned value** is the work actually done, valued at the budget. If a 100 project is 40% complete, its earned value is 40, even if 50 has been spent. Comparing earned value with what was spent and what was planned shows whether a project is over cost or late.",
            "O **valor agregado** é o trabalho realmente feito, valorizado pelo orçamento. Se um projeto de 100 está com 40% de avanço, seu valor agregado é 40, mesmo que se tenha gasto 50. Comparar com o gasto e o planejado mostra se o projeto está caro ou atrasado.")),
    dict(id="cost_efficiency", q=["qué es la eficiencia de costo", "eficiencia de costo", "cpi", "índice de desempeño del costo", "what is cost efficiency", "cost efficiency", "cost performance index", "o que é eficiência de custo", "eficiência de custo"],
         a=("La **eficiencia de costo** compara el trabajo hecho con lo gastado. **1,00** significa que se gasta exactamente lo presupuestado; **0,86** significa que por cada 1,00 gastado solo se logra 0,86 de trabajo: el proyecto va 14% más caro de lo previsto.",
            "**Cost efficiency** compares the work done with the money spent. **1.00** means spending exactly as budgeted; **0.86** means every 1.00 spent only delivers 0.86 of work: the project is running 14% over cost.",
            "A **eficiência de custo** compara o trabalho feito com o gasto. **1,00** significa gastar exatamente o orçado; **0,86** significa que cada 1,00 gasto entrega só 0,86 de trabalho: o projeto está 14% mais caro que o previsto.")),
    dict(id="schedule_efficiency", q=["qué es la eficiencia de plazo", "eficiencia de plazo", "spi", "índice de desempeño del cronograma", "what is schedule efficiency", "schedule efficiency", "schedule performance index", "o que é eficiência de prazo", "eficiência de prazo"],
         a=("La **eficiencia de plazo** compara el avance logrado con el avance que se había planificado a la fecha. **1,00** es ir a tiempo; **0,88** significa que se ha hecho el 88% de lo que debía estar hecho: el proyecto va atrasado.",
            "**Schedule efficiency** compares the progress achieved with the progress planned to date. **1.00** is on time; **0.88** means 88% of what should be done is done: the project is behind.",
            "A **eficiência de prazo** compara o avanço alcançado com o avanço previsto até a data. **1,00** é estar no prazo; **0,88** significa que 88% do que deveria estar feito foi feito: o projeto está atrasado.")),
    dict(id="eac", q=["qué es el costo estimado al cierre", "costo estimado al cierre", "costo final estimado", "eac", "what is the estimate at completion", "estimate at completion", "final cost forecast", "o que é o custo estimado no término", "custo estimado no término"],
         a=("El **costo estimado al cierre** es cuánto se espera que cueste el proyecto al terminar. Se calcula con lo ya gastado más el trabajo pendiente, ajustado por la eficiencia real de cada actividad hasta hoy.",
            "The **estimate at completion** is what the project is expected to cost when it finishes: what has been spent plus the remaining work, adjusted by each activity's actual cost efficiency so far.",
            "O **custo estimado no término** é quanto se espera que o projeto custe ao terminar: o já gasto mais o trabalho restante, ajustado pela eficiência real de cada atividade até hoje.")),
    dict(id="s_curve", q=["qué es la curva s", "curva s", "what is an s-curve", "s curve", "s-curve", "o que é a curva s"],
         a=("La **curva S** muestra el avance acumulado en el tiempo: lo planificado, lo realmente hecho (valor ganado) y lo gastado. Tiene forma de S porque las obras arrancan lento, aceleran en la mitad y frenan al final.",
            "The **S-curve** shows cumulative progress over time: what was planned, what was actually done (earned value) and what was spent. It is S-shaped because projects start slowly, speed up in the middle and slow down at the end.",
            "A **curva S** mostra o avanço acumulado no tempo: o previsto, o realmente feito (valor agregado) e o gasto. Tem forma de S porque as obras começam devagar, aceleram no meio e desaceleram no final.")),
    dict(id="row", q=["qué es el derecho de vía", "derecho de vía", "ddv", "what is the right of way", "right of way", "o que é a faixa de servidão", "faixa"],
         a=("El **derecho de vía** es la franja de terreno por donde pasa el ducto. Su apertura (desbroce y nivelación) es la primera actividad de campo de una línea.",
            "The **right of way** is the strip of land the pipeline runs along. Clearing and grading it is the first field activity on a pipeline.",
            "A **faixa** (faixa de servidão) é a área de terreno por onde passa o duto. Sua abertura e limpeza é a primeira atividade de campo de uma linha.")),
    dict(id="hdd", q=["qué es la perforación horizontal dirigida", "perforación dirigida", "cruce especial", "phd", "what is horizontal directional drilling", "hdd", "directional drilling", "o que é perfuração direcional", "mnd"],
         a=("La **perforación horizontal dirigida** es una técnica para cruzar ríos, carreteras o zonas sensibles por debajo, sin abrir zanja: se perfora un túnel curvo y se jala la tubería por dentro. Es de las actividades más costosas y riesgosas de un ducto.",
            "**Horizontal directional drilling** is a way to cross rivers, roads or sensitive areas underneath without digging a trench: a curved tunnel is drilled and the pipe is pulled through. It is one of the most expensive and risky pipeline activities.",
            "A **perfuração direcional** é uma técnica para atravessar rios, estradas ou áreas sensíveis por baixo, sem abrir vala: perfura-se um túnel curvo e puxa-se o tubo por dentro. É uma das atividades mais caras e arriscadas de um duto.")),
    dict(id="hydrotest", q=["qué es la prueba hidrostática", "prueba hidrostática", "what is a hydrotest", "hydrostatic test", "hydrotest", "o que é o teste hidrostático", "teste hidrostático"],
         a=("La **prueba hidrostática** llena el ducto terminado con agua a presión por encima de la de operación, para comprobar que no tiene fugas antes de ponerlo en servicio.",
            "The **hydrostatic test** fills the finished pipeline with water at a pressure above operating pressure, to prove it has no leaks before it goes into service.",
            "O **teste hidrostático** enche o duto pronto com água em pressão acima da de operação, para comprovar que não há vazamentos antes de entrar em serviço.")),
    dict(id="ndt", q=["qué son los ensayos no destructivos", "ensayos no destructivos", "radiografía de soldaduras", "end", "what is non-destructive testing", "ndt", "weld inspection", "o que são ensaios não destrutivos"],
         a=("Los **ensayos no destructivos** (como la radiografía o el ultrasonido) revisan cada soldadura sin dañarla. Las que no pasan se reparan; por eso la **tasa de reparación** es un indicador de calidad: por encima de 5% suele incumplir el contrato.",
            "**Non-destructive testing** (such as X-ray or ultrasound) checks every weld without damaging it. Welds that fail are repaired, which is why the **repair rate** is a quality indicator: above 5% usually breaches the contract.",
            "Os **ensaios não destrutivos** (como radiografia ou ultrassom) verificam cada solda sem danificá-la. As que falham são reparadas; por isso a **taxa de reparo** é um indicador de qualidade: acima de 5% costuma descumprir o contrato.")),
    dict(id="standby", q=["qué es el standby", "standby", "equipos parados", "what is standby", "idle equipment", "o que é standby", "equipamento parado"],
         a=("El **standby** es el tiempo en que equipos y cuadrillas están en obra pero no pueden trabajar (por lluvia, un paro o falta de permisos). Se paga igual, así que genera costo sin avance.",
            "**Standby** is time when equipment and crews are on site but cannot work (rain, a stoppage, missing permits). It is still paid, so it creates cost without progress.",
            "O **standby** é o tempo em que equipamentos e equipes estão na obra mas não podem trabalhar (chuva, paralisação, falta de licenças). É pago mesmo assim, gerando custo sem avanço.")),
    dict(id="anomaly", q=["qué es el costo sin avance", "costo sin avance", "anomalía de costo", "what is cost without progress", "cost anomaly", "o que é custo sem avanço", "anomalia de custo"],
         a=("Un **costo sin avance** es un mes en que una actividad gastó mucho más de lo que justifica el avance físico logrado. El sistema lo detecta solo y busca la causa en los informes y órdenes de cambio; si no la encuentra, lo marca como **sin explicación** para revisarlo.",
            "**Cost without progress** is a month where an activity spent far more than its physical progress justifies. The system detects it automatically and looks for the reason in reports and change orders; if it finds none, it flags it as **unexplained** for review.",
            "Um **custo sem avanço** é um mês em que uma atividade gastou muito mais do que justifica o avanço físico. O sistema detecta sozinho e procura a causa nos relatórios e ordens de alteração; se não encontra, marca como **sem explicação** para revisão.")),
    dict(id="reconciliation", q=["qué es la conciliación", "conciliación contable", "cuadrar la contabilidad con el excel", "what is reconciliation", "reconciliation", "o que é conciliação", "conciliação"],
         a=("La **conciliación** compara dos fuentes que deberían decir lo mismo. Aquí se compara la contabilidad (Dynamics GP) con el control de costos en Excel, proyecto por proyecto, mes por mes y tipo de costo por tipo de costo. Cada diferencia se muestra con la fila y la celda de origen.",
            "**Reconciliation** compares two sources that should say the same thing. Here the accounting system (Dynamics GP) is compared with the Excel cost control, by project, month and cost type. Every difference is shown with its source row and cell.",
            "A **conciliação** compara duas fontes que deveriam dizer o mesmo. Aqui se compara a contabilidade (Dynamics GP) com o controle de custos em Excel, por projeto, mês e tipo de custo. Cada diferença aparece com a linha e a célula de origem.")),
    dict(id="lineage", q=["qué es la trazabilidad", "trazabilidad", "de dónde sale este número", "what is traceability", "lineage", "where does this number come from", "o que é rastreabilidade", "rastreabilidade"],
         a=("**Trazabilidad** significa que cada número del sistema apunta al archivo exacto de donde salió: la celda del Excel, la página del PDF, la tarea del cronograma o la fila de la contabilidad. Haga clic en cualquier cifra para verlo.",
            "**Traceability** means every number in the system points to the exact place it came from: the Excel cell, PDF page, schedule task or accounting row. Click any figure to see it.",
            "**Rastreabilidade** significa que cada número do sistema aponta para o lugar exato de onde veio: a célula do Excel, a página do PDF, a tarefa do cronograma ou a linha da contabilidade. Clique em qualquer número para ver.")),
    dict(id="erp", q=["qué es un erp", "erp", "dynamics gp", "sistema contable", "what is an erp", "accounting system", "o que é um erp", "sistema contábil"],
         a=("Un **ERP** es el sistema de gestión y contabilidad de la empresa. Conduto usa **Microsoft Dynamics GP** y evalúa migrar a SAP o Dynamics 365. Esta solución funciona con cualquiera de ellos: hoy lee las exportaciones de GP y mañana puede conectarse al sistema nuevo.",
            "An **ERP** is the company's management and accounting system. Conduto uses **Microsoft Dynamics GP** and is evaluating a move to SAP or Dynamics 365. This solution works with any of them: today it reads GP exports, and later it can connect to the new system.",
            "Um **ERP** é o sistema de gestão e contabilidade da empresa. A Conduto usa o **Microsoft Dynamics GP** e avalia migrar para SAP ou Dynamics 365. Esta solução funciona com qualquer um: hoje lê exportações do GP e depois pode se conectar ao sistema novo.")),
    dict(id="inch_km", q=["qué es el costo por pulgada-km", "pulgada km", "costo por km", "what is cost per inch-km", "inch km", "o que é custo por polegada-km"],
         a=("El **costo por pulgada-km** divide el costo del ducto entre su diámetro (en pulgadas) y su longitud (en km). Permite comparar ductos de distinto tamaño en la misma escala: un ducto de 16 pulgadas y 50 km equivale a 800 pulgadas-km.",
            "**Cost per inch-km** divides a pipeline's cost by its diameter (in inches) times its length (in km). It puts pipelines of different sizes on the same scale: a 16-inch, 50 km line is 800 inch-km.",
            "O **custo por polegada-km** divide o custo do duto pelo diâmetro (em polegadas) vezes o comprimento (em km). Coloca dutos de tamanhos diferentes na mesma escala: um duto de 16 polegadas e 50 km equivale a 800 polegadas-km.")),
    dict(id="force_majeure", q=["qué es fuerza mayor", "fuerza mayor", "what is force majeure", "force majeure", "o que é força maior"],
         a=("**Fuerza mayor** es un evento imprevisible y fuera del control de las partes (por ejemplo, una pandemia o un desastre natural). Normalmente amplía el plazo, pero según el contrato puede no reconocer los costos de equipos parados.",
            "**Force majeure** is an unforeseeable event outside both parties' control (such as a pandemic or natural disaster). It usually extends the schedule, but depending on the contract it may not cover idle-equipment costs.",
            "**Força maior** é um evento imprevisível e fora do controle das partes (como uma pandemia ou desastre natural). Normalmente prorroga o prazo, mas conforme o contrato pode não cobrir custos de equipamentos parados.")),
    # ---------------- about the system
    dict(id="how_it_works", q=["cómo funciona este sistema", "cómo funciona", "qué hace esta plataforma", "how does this work", "how does the system work", "what does this platform do", "como funciona o sistema", "o que faz esta plataforma"],
         a=("Funciona en cuatro pasos: 1) **lee** los archivos que ya existen (Excel, Microsoft Project, PDF y exportaciones contables); 2) los **ordena** en una estructura común, con revisión humana; 3) **verifica** que las fuentes cuadren entre sí; 4) **muestra** márgenes, riesgos y hallazgos, con cada número enlazado a su origen.",
            "It works in four steps: 1) **reads** the files that already exist (Excel, Microsoft Project, PDF and accounting exports); 2) **organizes** them into one common structure, with human review; 3) **checks** that the sources agree; 4) **shows** margins, risks and findings, with every number linked to its source.",
            "Funciona em quatro passos: 1) **lê** os arquivos que já existem (Excel, Microsoft Project, PDF e exportações contábeis); 2) **organiza** tudo numa estrutura comum, com revisão humana; 3) **verifica** se as fontes conferem; 4) **mostra** margens, riscos e achados, com cada número ligado à origem.")),
    dict(id="real_data", q=["los datos son reales", "son datos reales", "de dónde vienen los datos", "estos números son reales", "is this real data", "is the data real", "where does the data come from", "os dados são reais", "de onde vêm os dados"],
         a=("En esta demostración **los datos son sintéticos**: 18 proyectos ficticios creados para mostrar el método, en los mismos formatos que usa Conduto. En la fase de diagnóstico el mismo sistema se alimenta con los archivos reales.",
            "In this demo **the data is synthetic**: 18 fictional projects created to show the method, in the same formats Conduto uses. In the discovery phase the same system is fed with the real files.",
            "Nesta demonstração **os dados são sintéticos**: 18 projetos fictícios criados para mostrar o método, nos mesmos formatos usados pela Conduto. Na fase de diagnóstico o mesmo sistema é alimentado com os arquivos reais.")),
    dict(id="accuracy", q=["qué tan preciso es", "es confiable", "puede equivocarse", "how accurate is it", "can it make mistakes", "is it reliable", "qual a precisão", "é confiável"],
         a=("Los números no los inventa ninguna inteligencia artificial: salen de la base de datos y cada uno enlaza a su origen. Los dos modelos entrenados (para leer etiquetas de Excel y para entender preguntas) aciertan cerca de 96% y 89% en pruebas escritas a mano; por eso cada importación la revisa una persona.",
            "No artificial intelligence invents the numbers: they come from the database and each one links to its source. The two trained models (for reading Excel labels and for understanding questions) score about 96% and 89% on hand-written tests, which is why a person reviews every import.",
            "Nenhuma inteligência artificial inventa os números: eles vêm do banco de dados e cada um aponta para a origem. Os dois modelos treinados (para ler rótulos do Excel e entender perguntas) acertam cerca de 96% e 89% em testes escritos à mão; por isso uma pessoa revisa cada importação.")),
    dict(id="security", q=["necesita internet", "dónde se guardan los datos", "es seguro", "do you need internet", "where is the data stored", "is it secure", "precisa de internet", "é seguro"],
         a=("El motor de este asistente funciona **sin internet** y sin enviar datos a terceros. En producción se instala en la nube propia de Conduto (por ejemplo, Azure) y todos los accesos a los sistemas de origen son de **solo lectura**.",
            "This assistant's engine runs **without internet** and without sending data to third parties. In production it is installed in Conduto's own cloud (for example, Azure) and all access to source systems is **read-only**.",
            "O motor deste assistente funciona **sem internet** e sem enviar dados a terceiros. Em produção é instalado na nuvem própria da Conduto (por exemplo, Azure) e todo acesso aos sistemas de origem é **somente leitura**.")),
    dict(id="connectors", q=["qué son los conectores", "conectores", "con qué sistemas se conecta", "integraciones", "cómo se conecta con nuestros sistemas",
                                "what are connectors", "connectors", "which systems can it connect to", "integrations", "how does it connect to our systems",
                                "o que são os conectores", "conectores", "com quais sistemas se conecta", "integrações"],
         a=("Los **conectores** leen los programas que Conduto ya usa, siempre en **modo de solo lectura**: las carpetas de proyecto (Excel, Microsoft Project y PDF), la contabilidad (Dynamics GP) y el sistema comercial (oportunidades y ofertas). Cada conector lleva los datos a un **modelo común**, así los tableros no dependen de ningún programa en particular. Están en la pantalla **Conectores**, con lo que lee cada uno, cada cuánto y su historial.",
            "**Connectors** read the programs Conduto already uses, always **read-only**: the project folders (Excel, Microsoft Project and PDF), accounting (Dynamics GP) and the sales system (opportunities and bids). Each connector brings the data into a **common model**, so the dashboards do not depend on any particular program. They are on the **Connectors** screen, with what each one reads, how often and its history.",
            "Os **conectores** leem os programas que a Conduto já usa, sempre em **modo somente leitura**: as pastas de projeto (Excel, Microsoft Project e PDF), a contabilidade (Dynamics GP) e o sistema comercial (oportunidades e propostas). Cada conector leva os dados a um **modelo comum**, assim os painéis não dependem de nenhum programa em particular. Estão na tela **Conectores**, com o que cada um lê, com que frequência e o histórico.")),
    dict(id="erp_change", q=["qué pasa si cambiamos a sap", "migración a dynamics 365", "cambio de sistema contable", "sirve con sap", "y cuando dejemos dynamics gp",
                                "what if we move to sap", "dynamics 365 migration", "accounting system change", "does it work with sap", "when we leave dynamics gp",
                                "e se mudarmos para o sap", "migração para dynamics 365", "troca do sistema contábil"],
         a=("En los tableros no cambia nada: solo se reemplaza el **conector** de Dynamics GP por el de SAP o el de Dynamics 365. Los indicadores se calculan sobre el modelo común, no sobre el sistema contable. Además, el histórico ya consolidado y limpio facilita la migración.",
            "Nothing changes in the dashboards: only the Dynamics GP **connector** is replaced by the SAP or Dynamics 365 one. Indicators are calculated on the common model, not on the accounting system. And the history, already consolidated and clean, makes the migration easier.",
            "Nos painéis nada muda: só se substitui o **conector** do Dynamics GP pelo do SAP ou do Dynamics 365. Os indicadores são calculados sobre o modelo comum, não sobre o sistema contábil. Além disso, o histórico já consolidado e limpo facilita a migração.")),
    dict(id="sales_system", q=["sistema comercial", "crm", "de dónde salen las ofertas", "oportunidades comerciales", "dynamics 365 sales",
                                  "sales system", "where do the bids come from", "sales opportunities", "sistema comercial", "de onde vêm as propostas"],
         a=("Las ofertas vienen del **sistema comercial** (en esta demostración, Dynamics 365 Sales) a través de su conector, cada hora. Cada oferta abierta se compara con lo que realmente costaron obras parecidas: la pantalla **Ofertas** marca las que quedan por debajo del histórico. Qué sistema comercial usa Conduto se confirma en el diagnóstico; el mismo conector sirve para Salesforce, HubSpot o una hoja de cálculo.",
            "Bids come from the **sales system** (in this demo, Dynamics 365 Sales) through its connector, every hour. Every open bid is compared with what similar jobs really cost: the **Bids** screen flags those priced below history. Which sales system Conduto uses is confirmed during discovery; the same connector works for Salesforce, HubSpot or a spreadsheet.",
            "As propostas vêm do **sistema comercial** (nesta demonstração, Dynamics 365 Sales) pelo seu conector, a cada hora. Cada proposta aberta é comparada com o que obras parecidas realmente custaram: a tela **Propostas** marca as que ficam abaixo do histórico. Qual sistema comercial a Conduto usa é confirmado no diagnóstico; o mesmo conector serve para Salesforce, HubSpot ou uma planilha.")),
    dict(id="upload", q=["cómo subo un archivo", "cómo importo datos", "cómo cargo un excel", "how do i upload a file", "how do i import data", "how to load an excel", "como envio um arquivo", "como importo dados"],
         a=("Vaya a **Cargar datos**, arrastre un Excel, un PDF o un cronograma de Microsoft Project (o use un archivo de ejemplo) y pulse **Leer este archivo**. El sistema muestra lo que entendió y marca lo dudoso; usted revisa y pulsa **Confirmar y guardar**.",
            "Go to **Load data**, drop an Excel file, a PDF or a Microsoft Project schedule (or use an example file) and click **Read this file**. The system shows what it understood and marks anything uncertain; you review it and click **Confirm and save**.",
            "Vá em **Carregar dados**, arraste um Excel, um PDF ou um cronograma do Microsoft Project (ou use um arquivo de exemplo) e clique em **Ler este arquivo**. O sistema mostra o que entendeu e marca o que é duvidoso; você revisa e clica em **Confirmar e salvar**.")),
    dict(id="next_steps", q=["cuánto tiempo toma implementarlo", "cuáles son los próximos pasos", "cuánto cuesta", "how long does it take to implement", "what are the next steps", "how much does it cost", "quanto tempo leva para implementar", "próximos passos"],
         a=("La propuesta es por fases: **diagnóstico** de 2 a 4 semanas con 2 o 3 proyectos reales; **piloto** en Ecuador de 6 a 8 semanas; y luego **escalar** a Perú y Brasil. El costo se define al terminar el diagnóstico, según el alcance acordado.",
            "The proposal is phased: a 2–4 week **discovery** with 2–3 real projects; a 6–8 week **pilot** in Ecuador; then **roll out** to Peru and Brazil. The cost is defined at the end of discovery, based on the agreed scope.",
            "A proposta é por fases: **diagnóstico** de 2 a 4 semanas com 2 ou 3 projetos reais; **piloto** no Equador de 6 a 8 semanas; depois **escalar** para Peru e Brasil. O custo é definido ao final do diagnóstico, conforme o escopo acordado.")),
    dict(id="conduto", q=["qué es conduto", "quién es conduto", "a qué se dedica conduto", "what is conduto", "who is conduto", "o que é a conduto"],
         a=("Según la reunión, **Conduto** construye ductos y obras civiles para oleoductos en varios países, entre ellos Ecuador, Perú y Brasil. Maneja mucha información de proyectos, hoy repartida en Excel, Microsoft Project y PDF.",
            "According to the meeting, **Conduto** builds pipelines and civil works for oil pipelines in several countries, including Ecuador, Peru and Brazil. It handles a lot of project information, today spread across Excel, Microsoft Project and PDFs.",
            "Segundo a reunião, a **Conduto** constrói dutos e obras civis para oleodutos em vários países, entre eles Equador, Peru e Brasil. Lida com muita informação de projetos, hoje espalhada em Excel, Microsoft Project e PDF.")),
    dict(id="languages", q=["en qué idiomas funciona", "hablas inglés", "idiomas", "what languages do you speak", "do you speak spanish", "languages", "quais idiomas", "fala português"],
         a=("Funciono en **español, inglés y portugués**. Puede cambiar el idioma con el selector de arriba a la derecha; también leo documentos escritos en cualquiera de los tres.",
            "I work in **Spanish, English and Portuguese**. Switch the language with the selector at the top right; I also read documents written in any of the three.",
            "Funciono em **espanhol, inglês e português**. Troque o idioma no seletor no canto superior direito; também leio documentos escritos em qualquer um dos três.")),
    # ---------------- small talk
    dict(id="greeting", q=["hola", "buenos días", "buenas tardes", "qué tal", "hello", "hi", "hey", "good morning", "olá", "oi", "bom dia", "boa tarde"],
         a=("¡Hola! Soy el asistente de proyectos de Conduto. Puedo contarle cómo van los proyectos, dónde se pierde margen, qué órdenes de cambio están pendientes o explicarle cualquier término. ¿En qué le ayudo?",
            "Hi! I'm Conduto's project assistant. I can tell you how projects are doing, where margin is being lost, which change orders are pending, or explain any term. How can I help?",
            "Olá! Sou o assistente de projetos da Conduto. Posso contar como vão os projetos, onde se perde margem, quais ordens de alteração estão pendentes ou explicar qualquer termo. Como posso ajudar?")),
    dict(id="thanks", q=["gracias", "muchas gracias", "perfecto gracias", "thanks", "thank you", "great thanks", "obrigado", "obrigada", "valeu"],
         a=("¡Con gusto! Si quiere, pregúnteme por otro proyecto o por la calidad de los datos.",
            "You're welcome! Feel free to ask about another project or about data quality.",
            "Por nada! Se quiser, pergunte sobre outro projeto ou sobre a qualidade dos dados.")),
    dict(id="bye", q=["adiós", "chao", "hasta luego", "bye", "goodbye", "see you", "tchau", "até logo"],
         a=("¡Hasta luego! Aquí estaré cuando necesite revisar los proyectos.",
            "Goodbye! I'll be here whenever you need to check the projects.",
            "Até logo! Estarei aqui quando precisar revisar os projetos.")),
    dict(id="how_are_you", q=["cómo estás", "qué tal estás", "how are you", "how are you doing", "como vai", "tudo bem"],
         a=("¡Muy bien, gracias! Listo para revisar los números. ¿Qué proyecto le interesa?",
            "Very well, thanks! Ready to look at the numbers. Which project are you interested in?",
            "Muito bem, obrigado! Pronto para revisar os números. Qual projeto interessa?")),
    dict(id="who_are_you", q=["quién eres", "qué eres", "qué puedes hacer", "en qué me ayudas", "who are you", "what are you", "what can you do", "quem é você", "o que você pode fazer"],
         a=("Soy el asistente de datos de Conduto. Respondo sobre márgenes, costos, atrasos, órdenes de cambio, eventos, soldadura, costos históricos, anomalías y la conciliación con la contabilidad; también explico conceptos. Cada cifra sale de la base de datos y cada cita abre el documento original.",
            "I'm Conduto's data assistant. I answer about margins, costs, delays, change orders, events, welding, historical costs, anomalies and the reconciliation with accounting; I also explain concepts. Every figure comes from the database and every citation opens the original document.",
            "Sou o assistente de dados da Conduto. Respondo sobre margens, custos, atrasos, ordens de alteração, ocorrências, soldagem, custos históricos, anomalias e a conciliação com a contabilidade; também explico conceitos. Cada número vem do banco de dados e cada citação abre o documento original.")),
]

OUT_OF_SCOPE = (
    "Esa pregunta está fuera de lo que puedo responder sin servicios externos: estoy preparado para los proyectos de Conduto y los conceptos de control de proyectos. Si se conecta Claude, también respondo preguntas generales de cualquier tema.",
    "That question is outside what I can answer without outside services: I'm prepared for Conduto's projects and project-control concepts. If Claude is connected, I also answer general questions on any topic.",
    "Essa pergunta está fora do que posso responder sem serviços externos: estou preparado para os projetos da Conduto e conceitos de controle de projetos. Se o Claude estiver conectado, também respondo perguntas gerais de qualquer tema.",
)


class FaqIndex:
    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer  # loaded on the first question
        from sklearn.pipeline import make_union

        self.texts, self.owner = [], []
        for i, e in enumerate(FAQ):
            for q in e["q"]:
                self.texts.append(content(q))
                self.owner.append(i)
        self.vec = make_union(
            TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True),
        )
        self.matrix = self.vec.fit_transform(self.texts)

    def best(self, question: str) -> tuple[dict | None, float]:
        q = self.vec.transform([content(question)])
        sims = (self.matrix @ q.T).toarray().ravel() / 2  # two blocks, each L2-normalized
        if not len(sims):
            return None, 0.0
        i = int(sims.argmax())
        return FAQ[self.owner[i]], float(sims[i])


_INDEX: FaqIndex | None = None


def index() -> FaqIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = FaqIndex()
    return _INDEX
