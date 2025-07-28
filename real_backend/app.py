import psycopg2
from psycopg2 import sql, errors
from datetime import datetime
from config import DATABASES

class PaymentIntegrator:
    def __init__(self):
        self.connections = {
            'accurate': self._connect('accurate'),
            'xendit': self._connect('xendit'),
            'paperid': self._connect('paperid')
        }
        self.existing_refs = self._load_existing_references()
        self.stats = {
            'total_processed': 0,
            'xendit_skipped': 0,
            'paperid_skipped': 0,
            'errors': 0
        }

    def _connect(self, db_key):
        """Establish database connection"""
        try:
            return psycopg2.connect(**DATABASES[db_key])
        except psycopg2.OperationalError as e:
            print(f"🚨 Connection failed to {db_key.upper()}: {str(e)}")
            raise

    def _load_existing_references(self):
        """Load existing payment references"""
        try:
            with self.connections['accurate'].cursor() as cur:
                cur.execute("""
                    SELECT CONCAT(metode_pembayaran, ':', nomor_penerimaan)
                    FROM penerimaan_penjualan
                """)
                return {row[0] for row in cur.fetchall()}
        except Exception as e:
            print(f"🔴 Failed loading references: {str(e)}")
            return set()

    def _process_payments(self, source):
        """Process payments from specified source"""
        payments = []
        try:
            with self.connections[source].cursor() as cur:
                cur.execute(f"""
                    SELECT tanggal, jumlah, nomor_invoice, id_student, 
                           {'id_xendit_payment' if source == 'xendit' else 'id_paper_payment'}, 
                           %s AS source
                    FROM payments
                """, (source,))
                
                for payment in cur.fetchall():
                    ref_id = f"{payment[5]}:{payment[4]}"
                    if ref_id in self.existing_refs:
                        self.stats[f'{source}_skipped'] += 1
                    else:
                        payments.append(payment)
                        self.existing_refs.add(ref_id)
            return payments
        except Exception as e:
            print(f"🔴 Error processing {source} payments: {str(e)}")
            self.stats['errors'] += 1
            return []

    def _calculate_total_payments(self):
        """Update jumlah_pembayaran in penerimaan_penjualan"""
        try:
            with self.connections['accurate'].cursor() as cur:
                cur.execute("""
                    UPDATE piutang_tagihan pp
                    SET jumlah_pembayaran = (
                        SELECT SUM(jumlah) 
                        FROM penerimaan_penjualan 
                        WHERE nomor_invoice = pp.nomor_invoice
                    )
                    WHERE pp.tanggal_update = CURRENT_DATE
                """)
                self.connections['accurate'].commit()
        except Exception as e:
            self.connections['accurate'].rollback()
            print(f"🔴 Failed calculating payments: {str(e)}")
            self.stats['errors'] += 1

    def _update_piutang_status(self):
        """Update status in piutang_tagihan"""
        try:
            with self.connections['accurate'].cursor() as cur:
                cur.execute("""
                    WITH payment_data AS (
                        SELECT 
                            pt.nomor_invoice,
                            SUM(pp.jumlah) AS total_bayar,
                            MAX(pp.tanggal) AS tanggal
                        FROM piutang_tagihan pt
                        JOIN penerimaan_penjualan pp ON pt.nomor_invoice = pp.nomor_invoice
                        GROUP BY pt.nomor_invoice
                    )
                    UPDATE piutang_tagihan pt
                    SET 
                        status = CASE 
                            WHEN (pt.total - pd.total_bayar) = 0 THEN 'Lunas'
                            WHEN (pt.total - pd.total_bayar) < 0 THEN 'Over Paid' -- Perhatikan perubahan ini untuk "Over Paid"
                            ELSE 'Belum Lunas'
                        END,
                        tanggal_update = pd.tanggal,
                        jumlah_pembayaran = pd.total_bayar
                    FROM payment_data pd
                    WHERE pt.nomor_invoice = pd.nomor_invoice
                """)
                self.connections['accurate'].commit()
        except Exception as e:
            self.connections['accurate'].rollback()
            print(f"🔴 Failed updating piutang status: {str(e)}")
            self.stats['errors'] += 1

    def _update_student_balances(self):
        """Update student total_tagihan"""
        try:
            with self.connections['accurate'].cursor() as cur:
                cur.execute("""
                    UPDATE students s
                    SET 
                        total_tagihan = pt.total - pt.jumlah_pembayaran,
                        tanggal_update = NOW()
                    FROM piutang_tagihan pt
                    WHERE s.id_student = pt.id_student
                    
                """)
                self.connections['accurate'].commit()
        except Exception as e:
            self.connections['accurate'].rollback()
            print(f"🔴 Failed updating student balances: {str(e)}")
            self.stats['errors'] += 1

    def integrate_payments(self):
        """Main integration workflow"""
        try:
            # Process both payment sources
            xendit_payments = self._process_payments('xendit')
            paperid_payments = self._process_payments('paperid')
            all_payments = xendit_payments + paperid_payments

            if not all_payments:
                print("🟡 No new payments to integrate")
                return False

            # Transform and insert payments
            transformed = [
                (p[3], p[0], p[2], p[1], p[4], p[5], datetime.now())
                for p in all_payments
            ]

            with self.connections['accurate'].cursor() as cur:
                cur.executemany("""
                    INSERT INTO penerimaan_penjualan 
                    (id_student, tanggal, nomor_invoice, jumlah, 
                     nomor_penerimaan, metode_pembayaran, tanggal_update)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, transformed)
                
            self.connections['accurate'].commit()
            self.stats['total_processed'] = len(transformed)
            
            # Execute post-processing steps
            self._calculate_total_payments()
            self._update_piutang_status()
            self._update_student_balances()
            
            print("✅ Integration succeeded!")
            self._show_stats()
            return True

        except errors.UniqueViolation:
            self.connections['accurate'].rollback()
            print("🔴 Failed: Duplicate entries detected")
            return False
        except Exception as e:
            self.connections['accurate'].rollback()
            print(f"🔴 Critical failure: {str(e)}")
            return False
        finally:
            for conn in self.connections.values():
                if conn and not conn.closed:
                    conn.close()

    def _show_stats(self):
        """Display integration statistics"""
        print("\n📊 Integration Report:")
        print(f"• Successfully processed: {self.stats['total_processed']}")
        print(f"• Xendit duplicates skipped: {self.stats['xendit_skipped']}")
        print(f"• PaperID duplicates skipped: {self.stats['paperid_skipped']}")
        print(f"• Total errors encountered: {self.stats['errors']}")

if __name__ == "__main__":
    integrator = PaymentIntegrator()
    success = integrator.integrate_payments()
    
    if not success:
        print("\n❌ Action required: Check error logs and retry")