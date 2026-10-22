# Montamar — demo guide

Everything you need to run the call. Ten minutes of reading.

---

## What this is

A working demo of the two things Montamar asked for on the discovery call:

1. **Supplier invoices go into Bejerman by themselves.** Their confirmed
   pain: one employee spends every morning typing them in.
2. **The field data ends up in one place**, checked and traceable back to
   the file it came from. Their second, less certain, ask.

Nothing else. The screens about building pipelines — portfolio margins,
bid comparisons, cost per kilometre — were removed. Montamar *protects*
pipelines; showing them someone else's business is what the call warned
against.

---

## The numbers

| | |
|---|---|
| Invoices in the month | **143** |
| Of those, on paper (scans + phone photos) | **54** |
| Posted into Bejerman with nobody typing | **110** |
| Still approved and waiting (so Sync does something live) | **15** |
| Stopped, waiting for a person | **18** |
| **Straight through** | **87.4%** |
| Typing removed | **~9.5 hours** a month on this batch |

The 18 that stopped: 4 expired authorisation codes, 3 billed to the other
company in the group, 3 that do not add up, 3 unknown suppliers, 3
duplicates, 2 invalid tax numbers.

**No correct invoice was wrongly stopped, and no planted problem got
through.** That is the number worth quoting.

---

## Running it (10 minutes)

### 1 · Open on the Overview (1 min)

> "Dos cosas: las facturas entran solas al sistema contable, y todo lo que
> llega por correo, carpetas y plataformas queda en un solo lugar."

Point at the three figures: **143 recibidas · 110 registradas sin tipear ·
18 esperan a una persona**, and the dark panel: **horas no tecleadas**.

Then the channel strip underneath: **33 escaneadas, 21 fotos de papel**.

> "Cincuenta y cuatro de esas no son archivos. Son papel — escaneado o
> fotografiado con el teléfono. Entran por la misma puerta."

### 2 · Facturas — open one that worked (2 min)

Click any invoice marked **Registrada**. The panel shows every check in
the order it ran: tipo de comprobante, CAE, CUIT del emisor, emitida a
nuestro CUIT, IVA, suma, no duplicada.

> "Cada verificación es aritmética o una búsqueda. Ninguna la decide un
> modelo."

### 3 · Open one that stopped (2 min) — **the important one**

Filter to **Detenida**. Pick the one with *CAE vencido*.

> "No se registró. Y dice por qué, en una línea que un contador entiende."

Then press **Aprobar igual**.

> "Una persona puede pasarla por encima. La excepción no se borra: queda
> con el nombre de quien decidió."

### 4 · The three Argentine traps (2 min)

Find a **Factura B** and a **Factura C** in the list.

> "Una Factura B lleva el IVA adentro del precio. Una C no discrimina IVA.
> Un lector que exige una línea de IVA marca las dos como error, y alguien
> las limpia a mano todas las mañanas. Acá pasan, porque el sistema sabe
> qué tipo de comprobante está leyendo."

Then find one with **percepción**:

> "Y con una percepción de Ingresos Brutos, neto más IVA no da el total.
> El que insiste en que dé, rechaza media Argentina."

### 5 · Press Sync (1 min)

Back on Facturas → **Registrar 15 en Bejerman**.

They go in. Press it again: **nothing posts twice.**

### 6 · Conectores → Bejerman (1 min) — **the question they will ask**

> "Nicolás dijo que no sabe si Bejerman tiene interfaz de importación.
> No hace falta saberlo para empezar."

The connector shows **both routes**: write through an import interface if
there is one, or enter it through the same screen a person uses if there
isn't. The demo is built on the second — the one that always works.

> "Y en los dos casos el sistema sólo agrega comprobantes nuevos. No
> modifica ni borra nada de lo ya cargado, así que la conexión con el
> estudio contable queda intacta."

### 7 · The estimator (1 min)

Foot of the Facturas page. Put in **their** volume and **their** minutes.

Let Nicolás type the numbers himself. He has to take this to management on
ROI, and a figure he entered is one he can defend.

---

## Questions you will get

**"¿Funciona con nuestro Bejerman?"**
Two routes, and the demo runs the one that works without an interface. The
first thing discovery settles is which of the two applies.

**"¿Y si lee mal una factura?"**
It stops and says why. In this batch nothing correct was stopped and
nothing wrong got through — but when it is unsure it holds, it does not
guess. Every figure on screen opens to show where it was read from.

**"¿Puede romper algo en la contabilidad?"**
It only adds documents a person approved. It never edits or deletes what
is already posted. And the same document cannot go in twice — the
reference the accounting system gives back is the proof it already went.

**"¿Y los archivos SHP y los datos geoespaciales?"**
Not yet. It is the next step of the consolidation, and the Overview page
says so out loud. Do not promise it.

**"¿De dónde salen estos números?"**
All invented. The suppliers, amounts and invoices are not Montamar's. The
*rules* are real: CUIT, CAE, Factura A/B/C, IVA, percepciones.

---

## Say this, not that

| Don't say | Say |
|---|---|
| "It's 100% automatic" | "87% go in untouched. The rest stop and say why." |
| "It replaces the employee" | "It gives back the morning. The exceptions still need a person." |
| "It integrates with Bejerman" | "Two routes, and we have the one that works whether or not it has an interface." |
| "AI reads the invoices" | "It reads them, then arithmetic checks them. No model decides a number." |

---

## The one thing to lead with

Everyone sells time savings. Lead with this instead:

> "Además del tiempo, bloquea las facturas duplicadas y los cambios de
> CBU. Tres duplicadas en este mes, y cada una habría sido un pago doble."

Time savings is why the employee will like it. **Blocking a double payment
is why the finance director signs it.**

---

## If something goes wrong on the call

- **A screen is empty** → press **Reiniciar demo** bottom-left, wait ~30s.
- **Figures look odd** → they are synthetic; say so and move on.
- **Sync posts nothing** → everything is already posted. That is correct
  behaviour, and it is the duplicate protection working.
