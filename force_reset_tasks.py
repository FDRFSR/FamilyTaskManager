import os
import psycopg2

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL non impostato!")

    default_tasks = [
        ("cucina_pulizia", "Pulizia cucina", 10, 20),
        ("bagno_pulizia", "Pulizia bagno", 12, 25),
        ("spazzatura", "Portare fuori la spazzatura", 5, 5),
        ("bucato", "Fare il bucato", 8, 15),
        ("giardino", "Cura del giardino", 15, 30),
        ("spesa", "Fare la spesa", 7, 20),
        ("cena", "Preparare la cena", 10, 25),
        ("camera", "Riordinare la camera", 6, 10),
        ("animali", "Dare da mangiare agli animali", 4, 5),
        ("auto", "Lavare l'auto", 13, 30),
        ("lavastoviglie", "Caricare lavastoviglie", 6, 8),
        ("stendere_bucato", "Stendere il bucato", 6, 10),
        ("aspirapolvere", "Passare l’aspirapolvere", 8, 15),
        ("svuotare_lavastoviglie", "Svuotare la lavastoviglie", 5, 5),
        ("riordinare_soggiorno", "Riordinare il soggiorno", 6, 10),
        ("buttare_rifiuti", "Buttare la carta/vetro/plastica", 5, 5),
        ("fare_letti", "Fare i letti", 4, 5),
        ("preparare_tavola", "Preparare la tavola", 4, 5),
        ("sparecchiare_tavola", "Sparecchiare la tavola", 4, 5),
        ("lettiera_gatto", "Pulire la lettiera del gatto", 6, 8),
        ("pulire_garage", "Pulire il garage", 15, 30),
        ("pulire_finestre", "Pulire le finestre", 10, 20),
        ("organizzare_armadi", "Organizzare gli armadi", 12, 25),
        ("pulire_frigorifero", "Pulire il frigorifero", 8, 15),
        ("innaffiare_piante", "Innaffiare le piante", 3, 5),
        ("pulire_specchi", "Pulire gli specchi", 5, 10),
        ("cambiare_lenzuola", "Cambiare le lenzuola", 7, 15),
        ("pulire_forno", "Pulire il forno", 12, 25),
        ("raccogliere_foglie", "Raccogliere le foglie", 8, 20),
        ("pulire_balcone", "Pulire il balcone", 6, 15),
        ("organizzare_cantina", "Organizzare la cantina", 15, 40),
        ("pulire_scarpe", "Pulire le scarpe", 4, 10),
        ("spolverare_mobili", "Spolverare i mobili", 6, 15),
        ("pulire_elettrodomestici", "Pulire gli elettrodomestici", 10, 20),
        ("riordinare_scrivania", "Riordinare la scrivania", 5, 10),
        ("pulire_tappeti", "Pulire i tappeti", 9, 20),
        ("organizzare_garage", "Organizzare il garage", 18, 45),
        ("pulire_scale", "Pulire le scale", 7, 15),
        ("cambiare_filtri", "Cambiare i filtri dell'aria", 8, 20),
        ("pulire_ventilatori", "Pulire i ventilatori", 6, 15),
        ("organizzare_dispensa", "Organizzare la dispensa", 10, 25)
    ]

    with psycopg2.connect(db_url, sslmode='require') as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks;")
        for t in default_tasks:
            cur.execute(
                "INSERT INTO tasks (id, name, points, time_minutes) VALUES (%s, %s, %s, %s);",
                t
            )
        conn.commit()
    print("Tutte le task sono state sovrascritte con la lista di default.")

if __name__ == "__main__":
    main()
