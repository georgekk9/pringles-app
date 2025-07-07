import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import uuid

DB = "pringles_wms.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    # ... Tabellen wie gehabt anlegen (du kannst sie einfach aus deinem alten Code übernehmen!) ...
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sorten (
            sorte_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lager (
            dose_id TEXT PRIMARY KEY,
            sorte_id INTEGER,
            mhd DATE,
            status TEXT,
            eingelagert_am DATE,
            FOREIGN KEY (sorte_id) REFERENCES sorten (sorte_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS automat (
            automat_id TEXT PRIMARY KEY,
            standort TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verkauf (
            verkauf_id TEXT PRIMARY KEY,
            automat_id TEXT,
            datum DATE,
            menge INTEGER,
            bargeld REAL,
            FOREIGN KEY (automat_id) REFERENCES automat (automat_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ausgaben (
            ausgabe_id TEXT PRIMARY KEY,
            datum DATE,
            betrag REAL,
            kategorie TEXT,
            kommentar TEXT,
            art TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kontobewegung (
            bewegung_id TEXT PRIMARY KEY,
            datum DATE,
            betrag REAL,
            art TEXT,
            kommentar TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS privatentnahme (
            id INTEGER PRIMARY KEY,
            betrag REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_sorten():
    conn = get_conn()
    sorten = conn.execute('SELECT sorte_id, name FROM sorten').fetchall()
    conn.close()
    return sorten

def add_sorte(name):
    conn = get_conn()
    conn.execute('INSERT OR IGNORE INTO sorten (name) VALUES (?)', (name,))
    conn.commit()
    conn.close()

def add_dosen(sorte_id, mhd, menge):
    conn = get_conn()
    for _ in range(menge):
        dose_id = str(uuid.uuid4())
        conn.execute(
            'INSERT INTO lager (dose_id, sorte_id, mhd, status, eingelagert_am) VALUES (?, ?, ?, ?, ?)',
            (dose_id, sorte_id, mhd, 'lager', datetime.now().date()))
    conn.commit()
    conn.close()

def get_lager():
    conn = get_conn()
    res = conn.execute('''
        SELECT s.name, l.mhd, COUNT(*) as anzahl
        FROM lager l
        LEFT JOIN sorten s ON l.sorte_id = s.sorte_id
        WHERE l.status = "lager"
        GROUP BY s.name, l.mhd
        ORDER BY s.name, l.mhd
    ''').fetchall()
    conn.close()
    return res

def add_automat(automat_id, standort):
    conn = get_conn()
    conn.execute('INSERT OR IGNORE INTO automat (automat_id, standort) VALUES (?, ?)', (automat_id, standort))
    conn.commit()
    conn.close()

def get_automaten():
    conn = get_conn()
    res = conn.execute('SELECT * FROM automat').fetchall()
    conn.close()
    return res

def befuellung_vorschlagen():
    conn = get_conn()
    sorten = conn.execute('''
        SELECT s.sorte_id, s.name, COUNT(*) as anzahl
        FROM lager l
        LEFT JOIN sorten s ON l.sorte_id = s.sorte_id
        WHERE l.status="lager"
        GROUP BY s.sorte_id
        ORDER BY s.name
    ''').fetchall()
    conn.close()
    vorschlag = []
    dosen_gesamt = 0
    reihen_liste = []
    for sorte_id, name, anzahl in sorten:
        reihen = anzahl // 7
        if reihen > 0:
            reihen_liste.append([sorte_id, name, reihen])
    while dosen_gesamt + 7 <= 49 and any(r[2] > 0 for r in reihen_liste):
        for r in reihen_liste:
            if r[2] > 0 and dosen_gesamt + 7 <= 49:
                vorschlag.append((r[1], 7))
                dosen_gesamt += 7
                r[2] -= 1
    return vorschlag

def add_verkauf(automat_id, menge, bargeld):
    conn = get_conn()
    verkauf_id = str(uuid.uuid4())
    conn.execute('INSERT INTO verkauf (verkauf_id, automat_id, datum, menge, bargeld) VALUES (?, ?, ?, ?, ?)',
                 (verkauf_id, automat_id, datetime.now().date(), menge, bargeld))
    conn.commit()
    conn.close()

def add_ausgabe(betrag, kategorie, kommentar, art):
    conn = get_conn()
    ausgabe_id = str(uuid.uuid4())
    conn.execute('INSERT INTO ausgaben (ausgabe_id, datum, betrag, kategorie, kommentar, art) VALUES (?, ?, ?, ?, ?, ?)',
                 (ausgabe_id, datetime.now().date(), betrag, kategorie, kommentar, art))
    conn.commit()
    conn.close()

def add_kontobewegung(betrag, art, kommentar):
    conn = get_conn()
    bewegung_id = str(uuid.uuid4())
    conn.execute('INSERT INTO kontobewegung (bewegung_id, datum, betrag, art, kommentar) VALUES (?, ?, ?, ?, ?)',
                 (bewegung_id, datetime.now().date(), betrag, art, kommentar))
    conn.commit()
    conn.close()

def get_kontobewegungen():
    conn = get_conn()
    data = conn.execute('SELECT datum, betrag, art, kommentar FROM kontobewegung ORDER BY datum').fetchall()
    conn.close()
    return data

def get_finanzuebersicht():
    conn = get_conn()
    bar = conn.execute('SELECT SUM(bargeld) FROM verkauf').fetchone()[0] or 0
    ausgaben_bar = conn.execute('SELECT SUM(betrag) FROM ausgaben WHERE art="bar"').fetchone()[0] or 0
    konto = conn.execute('SELECT SUM(betrag) FROM kontobewegung').fetchone()[0] or 0
    ausgaben_konto = conn.execute('SELECT SUM(betrag) FROM ausgaben WHERE art="konto"').fetchone()[0] or 0
    privat = conn.execute('SELECT betrag FROM privatentnahme WHERE id=1').fetchone()
    privatentnahme = privat[0] if privat else 0
    kasse = bar - ausgaben_bar - privatentnahme
    gewinn = bar + konto - (ausgaben_bar + ausgaben_konto)
    conn.close()
    return {
        "Bargeld-Einnahmen": bar,
        "Bar-Ausgaben": ausgaben_bar,
        "Konto-Umsatz": konto,
        "Konto-Ausgaben": ausgaben_konto,
        "Privatentnahme": privatentnahme,
        "Kassenstand": kasse,
        "Gesamtgewinn": gewinn
    }

def privat_entnahme_nehmen(betrag):
    conn = get_conn()
    row = conn.execute('SELECT betrag FROM privatentnahme WHERE id=1').fetchone()
    bisher = row[0] if row else 0
    neu = bisher + betrag
    if row:
        conn.execute('UPDATE privatentnahme SET betrag=? WHERE id=1', (neu,))
    else:
        conn.execute('INSERT INTO privatentnahme (id, betrag) VALUES (1, ?)', (neu,))
    conn.commit()
    conn.close()

def privat_entnahme_rueckgabe(betrag):
    conn = get_conn()
    row = conn.execute('SELECT betrag FROM privatentnahme WHERE id=1').fetchone()
    bisher = row[0] if row else 0
    neu = max(0, bisher - betrag)
    if row:
        conn.execute('UPDATE privatentnahme SET betrag=? WHERE id=1', (neu,))
    else:
        conn.execute('INSERT INTO privatentnahme (id, betrag) VALUES (1, ?)', (neu,))
    conn.commit()
    conn.close()

# -------------------- Streamlit Oberfläche --------------------

st.set_page_config(page_title="Pringles Automaten WMS", page_icon="🥔")

st.title("🥔 Pringles Automaten Warenwirtschaft")
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Lager", "Automaten", "Befüllung", "Verkauf", "Ausgaben/Konto", "Finanzen", "Privat"
])

with tab1:
    st.header("Lagerverwaltung")
    if st.button("Lager anzeigen/aktualisieren"):
        lager = get_lager()
        for name, mhd, anzahl in lager:
            st.write(f"{name} - {mhd}: {anzahl} Dosen")
    st.subheader("Dose(n) ins Lager einfügen")
    sorten = get_sorten()
    sorten_namen = [s[1] for s in sorten]
    if len(sorten) > 0:
        sorte_idx = st.selectbox("Sorte auswählen", range(len(sorten)), format_func=lambda i: sorten[i][1])
        menge = st.number_input("Wieviele Dosen?", min_value=1, max_value=500, value=7)
        mhd = st.date_input("MHD (Mindesthaltbarkeitsdatum)", min_value=datetime.now())
        if st.button("Dose(n) einlagern"):
            add_dosen(sorten[sorte_idx][0], mhd.strftime("%Y-%m-%d"), menge)
            st.success("Dose(n) eingelagert!")
    st.subheader("Neue Sorte anlegen")
    new_sorte = st.text_input("Sortenname")
    if st.button("Sorte speichern"):
        add_sorte(new_sorte)
        st.success("Sorte gespeichert!")

with tab2:
    st.header("Automatenverwaltung")
    automaten = get_automaten()
    for a in automaten:
        st.write(f"{a[0]} – {a[1]}")
    automat_id = st.text_input("Neue Automat-ID")
    standort = st.text_input("Standort")
    if st.button("Automat hinzufügen"):
        add_automat(automat_id, standort)
        st.success("Automat hinzugefügt!")

with tab3:
    st.header("Befüllvorschlag (nur volle 7er-Reihen, max. 49 Dosen)")
    vorschlag = befuellung_vorschlagen()
    if vorschlag:
        for name, anzahl in vorschlag:
            st.write(f"{name}: {anzahl} Dosen")
        st.write(f"Gesamt: {sum(v[1] for v in vorschlag)} Dosen")
    else:
        st.info("Nicht genug volle Reihen von einer Sorte im Lager!")

with tab4:
    st.header("Verkauf erfassen")
    automaten = get_automaten()
    if len(automaten) > 0:
        automat = st.selectbox("Automat auswählen", [a[0] for a in automaten])
        menge = st.number_input("Verkaufte Dosen", min_value=1, value=1)
        bargeld = st.number_input("Eingenommenes Bargeld (€)", min_value=0.0, value=0.0, step=0.01)
        if st.button("Verkauf speichern"):
            add_verkauf(automat, menge, bargeld)
            st.success("Verkauf gespeichert!")

with tab5:
    st.header("Ausgaben")
    betrag = st.number_input("Betrag (€)", min_value=0.0, value=0.0, step=0.01, key="ausgaben_betrag")
    kategorie = st.text_input("Kategorie", key="ausgaben_kategorie")
    kommentar = st.text_input("Kommentar", key="ausgaben_kommentar")
    art = st.selectbox("Bar oder Konto?", ["bar", "konto"])
    if st.button("Ausgabe speichern"):
        add_ausgabe(betrag, kategorie, kommentar, art)
        st.success("Ausgabe gespeichert!")

    st.header("Konto")
    betrag_konto = st.number_input("Betrag Konto (+=Einzahlung, -=Auszahlung)", min_value=-10000.0, max_value=10000.0, value=0.0, step=0.01, key="konto_betrag")
    kommentar_konto = st.text_input("Kommentar Konto", key="konto_kommentar")
    art_konto = "einzahlung" if betrag_konto >= 0 else "auszahlung"
    if st.button("Konto-Bewegung speichern"):
        add_kontobewegung(betrag_konto, art_konto, kommentar_konto)
        st.success("Konto-Bewegung gespeichert!")

    st.subheader("Konto-Umsätze anzeigen")
    kontos = get_kontobewegungen()
    if kontos:
        for k in kontos:
            st.write(f"{k[0]} | {k[2]:10} | {k[1]:8.2f} € | {k[3]}")

with tab6:
    st.header("Finanzübersicht")
    f = get_finanzuebersicht()
    st.write(f"Bargeld-Einnahmen:  {f['Bargeld-Einnahmen']:.2f} €")
    st.write(f"Bar-Ausgaben:       {f['Bar-Ausgaben']:.2f} €")
    st.write(f"Konto-Umsatz:       {f['Konto-Umsatz']:.2f} €")
    st.write(f"Konto-Ausgaben:     {f['Konto-Ausgaben']:.2f} €")
    st.write(f"Privatentnahme:     {f['Privatentnahme']:.2f} €")
    st.write(f"Kassenstand:        {f['Kassenstand']:.2f} €")
    st.write(f"Gesamtgewinn:       {f['Gesamtgewinn']:.2f} €")

with tab7:
    st.header("Privatentnahme")
    privat_entnahme = st.number_input("Betrag für Privatentnahme (+) oder Rückgabe (-)", min_value=-10000.0, max_value=10000.0, value=0.0, step=0.01)
    if st.button("Privatentnahme buchen"):
        if privat_entnahme > 0:
            privat_entnahme_nehmen(privat_entnahme)
            st.success("Privatentnahme gespeichert!")
        elif privat_entnahme < 0:
            privat_entnahme_rueckgabe(-privat_entnahme)
            st.success("Privat-Rückgabe gespeichert!")
        else:
            st.info("Bitte Betrag eingeben!")

st.markdown("---")
st.markdown("**Tipp:** Um diese App auf dem Handy zu benutzen, einfach am iPhone im Browser diese Seite öffnen und über das 'Teilen'-Symbol zum Home-Bildschirm hinzufügen!")
