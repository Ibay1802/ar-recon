import csv
import psycopg2
import argparse

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="dummy_accurate",
        user="postgres",
        password="1234"
    )
    return conn

def insert_student(data, conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM students WHERE id_student = %s", (data['id_student'],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO students (id_student, name, email) VALUES (%s, %s, %s)",
                           (data['id_student'], data['name'], data['email']))
            conn.commit()
            print(f"Inserted student: {data['id_student']}")
        else:
            print(f"Student already exists: {data['id_student']}")
    except Exception as e:
        print(f"Error inserting student: {e}")
        conn.rollback()
    finally:
        cursor.close()

def insert_invoice(data, conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM piutang_tagihan WHERE nomor_invoice = %s", (data['nomor_invoice'],))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""INSERT INTO piutang_tagihan (nomor_invoice, id_student, tanggal, total, status)
                              VALUES (%s, %s, %s, %s, %s)""",
                           (data['nomor_invoice'], data['id_student'], data['tanggal'], data['total'], data['status']))
            conn.commit()
            print(f"Inserted invoice: {data['nomor_invoice']}")
        else:
            print(f"Invoice already exists: {data['nomor_invoice']}")
    except Exception as e:
        print(f"Error inserting invoice: {e}")
        conn.rollback()
    finally:
        cursor.close()

def insert_payment(data, conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM penerimaan_penjualan WHERE nomor_penerimaan = %s AND tanggal = %s",
                       (data['nomor_penerimaan'], data['tanggal']))
        if cursor.fetchone()[0] == 0:
            cursor.execute("""INSERT INTO penerimaan_penjualan 
                              (nomor_penerimaan, id_student, tanggal, jumlah, metode_pembayaran, nomor_invoice, tanggal_update)
                              VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                           (data['nomor_penerimaan'], data['id_student'], data['tanggal'], data['jumlah'],
                            data['metode_pembayaran'], data['nomor_invoice']))
            conn.commit()
            print(f"Inserted payment: {data['nomor_penerimaan']}")
        else:
            print(f"Payment already exists: {data['nomor_penerimaan']}")
    except Exception as e:
        print(f"Error inserting payment: {e}")
        conn.rollback()
    finally:
        cursor.close()

def process_csv(file_path, table_name, conn):
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        print(f"Processing {table_name} CSV: {file_path}")
        print(f"CSV headers: {reader.fieldnames}")
        for row in reader:
            try:
                if table_name == 'students':
                    insert_student(row, conn)
                elif table_name == 'piutang_tagihan':
                    insert_invoice(row, conn)
                elif table_name == 'penerimaan_penjualan' and row.get('metode_pembayaran') in ['BCA 1111', 'Kas Sementara']:
                    insert_payment(row, conn)
            except KeyError as e:
                print(f"Missing column {e} in row: {row}")
            except Exception as e:
                print(f"Error processing row {row}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV data into database.")
    parser.add_argument('--students', help='Path to students CSV file')
    parser.add_argument('--invoice', help='Path to invoice CSV file')
    parser.add_argument('--payment', help='Path to payment CSV file')

    args = parser.parse_args()

    if not any([args.students, args.invoice, args.payment]):
        print("Please provide at least one CSV file with --students, --invoice, or --payment")
        exit(1)

    conn = get_db_connection()
    try:
        if args.students:
            process_csv(args.students, 'students', conn)
        if args.invoice:
            process_csv(args.invoice, 'piutang_tagihan', conn)
        if args.payment:
            process_csv(args.payment, 'penerimaan_penjualan', conn)
    finally:
        conn.close()
        print("Database connection closed.")
