import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
import numpy as np

# Database connection parameters
db_user = 'postgres'
db_pwd = '1234'
db_host = 'localhost'
db_port = 5432
db_name = 'dummy_accurate'

# Connect to Database
engine = create_engine(f'postgresql://{db_user}:{db_pwd}@{db_host}:{db_port}/{db_name}')

@st.cache_data(ttl=600)
def load_data():
    try:
        with engine.connect() as conn:
            students = pd.read_sql(text('SELECT * FROM students'), conn)
            acc_receivable = pd.read_sql(text('SELECT * FROM piutang_tagihan'), conn)
            payments = pd.read_sql(text('SELECT * FROM penerimaan_penjualan'), conn)
        return students, acc_receivable, payments
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def preprocess_data(students, acc_receivable, payments):
    # Convert date columns to datetime
    acc_receivable['tanggal'] = pd.to_datetime(acc_receivable['tanggal'], errors='coerce')
    payments['tanggal'] = pd.to_datetime(payments['tanggal'], errors='coerce')

    # Calculate outstanding amount per invoice
    acc_receivable['outstanding'] = acc_receivable['total'] - acc_receivable['jumlah_pembayaran']

    # Merge invoice with student info
    df_invoice = acc_receivable.merge(students[['id_student', 'name', 'email']], on='id_student', how='left')

    # Calculate overpayment per invoice (if any)
    df_invoice['overpayment'] = df_invoice['jumlah_pembayaran'] - df_invoice['total']
    df_invoice['overpayment'] = df_invoice['overpayment'].apply(lambda x: x if x > 0 else 0)

    return df_invoice

def filter_data(df_invoice, payments, selected_student, inv_date_range, pay_date_range, selected_pay_methods):
    # Filter by student
    if selected_student != 'All':
        df_invoice = df_invoice[df_invoice['id_student'] == selected_student]
        payments = payments[payments['id_student'] == selected_student]

    # Filter invoice by date range
    if inv_date_range:
        start_date, end_date = inv_date_range
        df_invoice = df_invoice[(df_invoice['tanggal'] >= pd.to_datetime(start_date)) & (df_invoice['tanggal'] <= pd.to_datetime(end_date))]

    # Filter payments by date range
    if pay_date_range:
        pay_start, pay_end = pay_date_range
        payments = payments[(payments['tanggal'] >= pd.to_datetime(pay_start)) & (payments['tanggal'] <= pd.to_datetime(pay_end))]

    # Filter payments by payment method
    if selected_pay_methods and 'All' not in selected_pay_methods:
        payments = payments[payments['metode_pembayaran'].isin(selected_pay_methods)]

    return df_invoice, payments

def plot_aging(df_aging):
    bins = [0, 30, 60, 90, 120, 9999]
    labels = ['0-30', '31-60', '61-90', '91-120', '120+']
    df_aging['days_overdue'] = (pd.Timestamp.today() - df_aging['tanggal']).dt.days
    df_aging['aging_bucket'] = pd.cut(df_aging['days_overdue'], bins=bins, labels=labels, right=False)
    aging_summary = df_aging.groupby('aging_bucket')['outstanding'].sum().reset_index()

    fig, ax = plt.subplots()
    sns.barplot(data=aging_summary, x='aging_bucket', y='outstanding', ax=ax, palette='Blues_d')
    ax.set_title("Outstanding Receivables by Aging Bucket (Days Overdue)")
    ax.set_ylabel("Outstanding Amount (Rp)")
    ax.set_xlabel("Aging Bucket (Days)")

    # Add numeric labels on bars
    for p in ax.patches:
        height = p.get_height()
        ax.annotate(f'{int(height):,}', (p.get_x() + p.get_width() / 2., height),
                    ha='center', va='bottom', fontsize=9, color='black', xytext=(0, 3),
                    textcoords='offset points')

    st.pyplot(fig)

def plot_payment_methods(payments_filtered):
    payment_method_summary = payments_filtered.groupby('metode_pembayaran')['jumlah'].sum().reset_index()

    # Group small payment methods into 'Others' if less than 3% of total
    total_amount = payment_method_summary['jumlah'].sum()
    payment_method_summary['pct'] = payment_method_summary['jumlah'] / total_amount
    large_methods = payment_method_summary[payment_method_summary['pct'] >= 0.03]
    small_methods = payment_method_summary[payment_method_summary['pct'] < 0.03]

    if not small_methods.empty:
        others_sum = small_methods['jumlah'].sum()
        large_methods = large_methods.append({'metode_pembayaran': 'Others', 'jumlah': others_sum, 'pct': others_sum/total_amount}, ignore_index=True)

    fig2, ax2 = plt.subplots()
    ax2.pie(large_methods['jumlah'], labels=large_methods['metode_pembayaran'], autopct='%1.1f%%', startangle=140)
    ax2.set_title("Payment Amount by Method")
    st.pyplot(fig2)

def main():
    st.title("Accounts Receivable & Customer Analysis Dashboard")

    # Load data with spinner
    with st.spinner('Loading data...'):
        students, acc_receivable, payments = load_data()
        if students.empty or acc_receivable.empty or payments.empty:
            st.warning("Data not available or failed to load.")
            return

        df_invoice = preprocess_data(students, acc_receivable, payments)

    # Sidebar filters
    st.sidebar.header("Filters")

    # Student filter
    student_options = ['All'] + sorted(students['id_student'].unique().tolist())
    selected_student = st.sidebar.selectbox("Select Student", options=student_options)

    # Invoice date range filter
    min_inv_date = df_invoice['tanggal'].min()
    max_inv_date = df_invoice['tanggal'].max()
    inv_date_range = st.sidebar.date_input("Invoice Date Range", [min_inv_date, max_inv_date])

    # Payment date range filter
    min_pay_date = payments['tanggal'].min()
    max_pay_date = payments['tanggal'].max()
    pay_date_range = st.sidebar.date_input("Payment Date Range", [min_pay_date, max_pay_date])

    # Payment method filter
    payment_methods = ['All'] + sorted(payments['metode_pembayaran'].unique().tolist())
    selected_pay_methods = st.sidebar.multiselect("Payment Methods", options=payment_methods, default=['All'])

    # Filter data based on selections
    df_invoice_filtered, payments_filtered = filter_data(df_invoice, payments, selected_student, inv_date_range, pay_date_range, selected_pay_methods)

    # Invoice Status Summary
    st.subheader("Invoice Status Summary")
    status_summary = df_invoice_filtered['status'].value_counts().reset_index()
    status_summary.columns = ['Status', 'Count']
    st.dataframe(status_summary)

    # KPI summary
    total_invoiced = df_invoice_filtered['total'].sum()
    total_paid = df_invoice_filtered['jumlah_pembayaran'].sum()
    total_outstanding = df_invoice_filtered.loc[df_invoice_filtered['outstanding'] > 0, 'outstanding'].sum()
    total_overpaid = df_invoice_filtered['overpayment'].sum()

    st.subheader("Summary KPIs")
    col1, col2, col3, col4 = st.columns(4)
    # To shorthen the monetary display
    def format_currency_short(num):
        if num >= 1_000_000_000:
            return f"Rp {num/1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"Rp {num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"Rp {num/1_000:.1f}K"
        else:
            return f"Rp {num:,.0f}"
        
    col1.metric("Total Invoiced", format_currency_short(total_invoiced))
    col2.metric("Total Paid", format_currency_short(total_paid))
    col3.metric("Total Outstanding", format_currency_short(total_outstanding))
    col4.metric("Total Overpaid", format_currency_short(total_overpaid))

    # Overpaid Students Section
    st.subheader("Overpaid Students")
    # Calculate total overpayment per student
    overpaid_students = df_invoice_filtered.groupby(['id_student', 'name'])['overpayment'].sum().reset_index()
    overpaid_students = overpaid_students[overpaid_students['overpayment'] > 0].sort_values(by='overpayment', ascending=False)

    if not overpaid_students.empty:
        st.dataframe(overpaid_students[['id_student', 'name', 'overpayment']])
    else:
        st.write("No overpaid students found.")

    # Aging Analysis (only outstanding invoices)
    st.subheader("Aging Analysis")
    df_aging = df_invoice_filtered[df_invoice_filtered['outstanding'] > 0].copy()
    if not df_aging.empty:
        plot_aging(df_aging)
    else:
        st.write("No outstanding invoices to analyze.")

    # Top Customers by Outstanding Amount
    st.subheader("Top Customers by Outstanding Amount")
    customer_outstanding = df_invoice_filtered.groupby(['id_student', 'name'])['outstanding'].sum().reset_index()
    customer_outstanding = customer_outstanding.sort_values(by='outstanding', ascending=False).head(10)
    st.dataframe(customer_outstanding)

     # --- Invoice Status Breakdown (no due date) ---
    st.subheader("Invoice Status Breakdown")

    def invoice_status_no_due(row):
        if row['outstanding'] == 0:
            return 'Paid'
        elif row['outstanding'] == row['total']:
            return 'Unpaid'
        elif 0 < row['outstanding'] < row['total']:
            return 'Partially Paid'
        else:
            return 'Overpaid'

    df_invoice_filtered['status'] = df_invoice_filtered.apply(invoice_status_no_due, axis=1)

    status_counts = df_invoice_filtered['status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Count']

    fig1, ax1 = plt.subplots()
    ax1.pie(status_counts['Count'], labels=status_counts['Status'], autopct='%1.1f%%', startangle=140, colors=sns.color_palette('pastel'))
    ax1.axis('equal')
    ax1.set_title("Invoice Status Distribution")
    st.pyplot(fig1)

    # Payment Method Distribution
    st.subheader("Payment Method Distribution")
    if not payments_filtered.empty:
        plot_payment_methods(payments_filtered)
    else:
        st.write("No payment data available for selected filters.")

      # --- Payments Trend Over Time by payment method ---
    st.subheader("Payments Trend Over Time by Payment method")

    # Group payments by date and payment method
    payments_time_method = payments.groupby(['tanggal', 'metode_pembayaran'])['jumlah'].sum().reset_index()
    payments_time_method = payments_time_method.sort_values('tanggal')

    fig3, ax3 = plt.subplots(figsize=(10,5))

    # Plot each payment method line
    for method in payments_time_method['metode_pembayaran'].unique():
        data = payments_time_method[payments_time_method['metode_pembayaran'] == method]
        ax3.plot(data['tanggal'], data['jumlah'], marker='o', linestyle='-', label=method)

    ax3.set_xlabel('Date')
    ax3.set_ylabel('Total Payments (Rp. Juta)')
    ax3.set_title('Payments Over Time by Payment Method')
    ax3.legend(title='Payment Method')
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig3)

    # Invoice and Payment Trends Over Time
    st.subheader("Invoice and Payment Trends Over Time")
    invoices_time = df_invoice_filtered.groupby('tanggal')['total'].sum().reset_index()
    payments_time = payments_filtered.groupby('tanggal')['jumlah'].sum().reset_index()

    fig3, ax3 = plt.subplots(figsize=(10,5))
    ax3.plot(invoices_time['tanggal'], invoices_time['total'], label='Invoices', marker='o')
    ax3.plot(payments_time['tanggal'], payments_time['jumlah'], label='Payments', marker='o')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Amount (Rp. Juta)')
    ax3.set_title('Invoices and Payments Over Time')
    ax3.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig3)

    # Detailed tables in expandable sections
    with st.expander("Show Filtered Invoice Data"):
        st.dataframe(df_invoice_filtered)

    with st.expander("Show Filtered Payment Data"):
        st.dataframe(payments_filtered)

if __name__ == "__main__":
    main()