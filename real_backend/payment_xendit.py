import csv
import psycopg2
import sys

# Koneksi ke database PostgreSQL
def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="dummy_xendit",  # Menggunakan database dummy_xendit
        user="postgres",
        password="1234"
    )
    return conn

# Fungsi untuk memasukkan data ke tabel payment
def insert_payment(data, conn):
    cursor = conn.cursor()
    try:
        # Cek apakah data dengan id_xendit_payment sudah ada
        cursor.execute("""
            SELECT COUNT(*) FROM payments WHERE id_xendit_payment = %s
        """, (data['id_xendit_payment'],))
        if cursor.fetchone()[0] == 0:  # Jika data belum ada, masukkan data
            cursor.execute("""
                INSERT INTO payments (id_xendit_payment, nomor_invoice, tanggal, jumlah, id_student)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['id_xendit_payment'], data['nomor_invoice'], data['tanggal'], data['jumlah'], data['id_student']))
            conn.commit()
            print(f"Data berhasil dimasukkan ke tabel payments: {data['id_xendit_payment']}")
        else:
            print(f"Data sudah ada di tabel payments: {data['id_xendit_payment']}")
    except Exception as e:
        print(f"Error saat memasukkan data ke tabel payments: {e}")
        conn.rollback()  # Rollback jika terjadi kesalahan
    finally:
        cursor.close()

# Fungsi utama untuk membaca CSV dan memasukkan data ke database
def process_csv(file_path, conn):
    with open(file_path, 'r') as file:
        # Tambahkan delimiter jika file menggunakan titik koma
        reader = csv.DictReader(file, delimiter=';')  # Sesuaikan delimiter jika diperlukan
        print(f"Proses file: {file_path} untuk tabel: payments")
        print(f"Header CSV: {reader.fieldnames}")  # Debug header CSV
        for row in reader:
            try:
                insert_payment(row, conn)
            except KeyError as e:
                print(f"Kolom tidak ditemukan: {e}. Baris yang menyebabkan error: {row}")
            except Exception as e:
                print(f"Error saat memproses baris: {row}. Detail error: {e}")

# Eksekusi program
if __name__ == "__main__":
    if len(sys.argv)!=2:
        print("Usage: python payment_xendit.py <csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]

    conn = get_db_connection()
    try:
        # Proses file CSV untuk tabel payment
        process_csv(csv_file, conn)
    finally:
        conn.close()
        print("Koneksi database ditutup.")
