import re

import matplotlib
import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import altair as alt
import hashlib
import plotly.graph_objects as go
import plotly.subplots as sp
from datetime import datetime

st.set_option('deprecation.showPyplotGlobalUse', False)
# matplotlib.use('TkAgg')
# Connect to SQLite database
conn = sqlite3.connect('pickup_laundary_data.db')
c = conn.cursor()

# Create pickup_data table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS pickup_laundary_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Name TEXT,
                Phone TEXT,
                Email TEXT,
                Pickup_Date TEXT,
                Pickup_Time TEXT,
                Status TEXT,
                Address TEXT,
                City TEXT,
                Postal_Code TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Pickup_ID INTEGER,
                Item_Name TEXT,
                Item_Price REAL,
                FOREIGN KEY (Pickup_ID) REFERENCES pickup_laundary_data (id) ON DELETE CASCADE
            )''')

# Create the users table with the updated schema
c.execute('''CREATE TABLE IF NOT EXISTS  users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT,
                Password TEXT,
                Email TEXT,
                Date TEXT
            )''')

# Create ledger table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS ledger (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                Customer_ID INTEGER,
                Date TEXT,
                Description TEXT,
                Amount REAL,
                FOREIGN KEY (Customer_ID) REFERENCES pickup_laundary_data (id) ON DELETE CASCADE
            )''')

# CSS styles
st.markdown(
    """
    <style>
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# Main app
def main():
    # App title
    st.title('Laundry Pickup App')
    page = st.sidebar.selectbox('Page',
                                ['Customer Requests', 'Admin Dashboard', 'Register User Dashboard', 'Customer Ledger',
                                 'Sales Dashboard', 'Deregister User'])

    # Customer Requests page
    if page == 'Customer Requests':
        show_customer_requests()
    # Admin Dashboard page
    elif page == 'Admin Dashboard':
        show_admin_dashboard()
    elif page == 'Register User Dashboard':
        register_user()
    elif page == 'Customer Ledger':
        show_customer_ledger()
    elif page == 'Sales Dashboard':
        show_sales_dashboard()
    elif page == 'Deregister User':
        deregister_user()


# User Registration
def register_user():
    st.header('User Registration')

    # Input form for user registration
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')
    confirm_password = st.text_input('Confirm Password', type='password')
    email = st.text_input('Email')
    date = st.date_input('Today date')

    # Validate form inputs and handle registration
    if st.button('Register'):
        if username and password and confirm_password and email:
            if password == confirm_password:
                # Hash the password using SHA-256 algorithm
                hashed_password = hashlib.sha256(password.encode()).hexdigest()

                # Check if the email address is already registered
                c.execute("SELECT * FROM users WHERE Email=?", (email,))
                existing_user = c.fetchone()

                if existing_user:
                    st.warning('Email address is already registered. Please use a different email address.')
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                    st.warning('Invalid email address. Please enter a valid email.')
                else:
                    # Insert the new user into the database
                    c.execute("INSERT INTO users (Username, Password, Email, Date) VALUES (?, ?, ?,?)",
                              (username, hashed_password, email, date))
                    conn.commit()
                    st.success('Registration successful. You can now login with your username and password.')
            else:
                st.warning('Passwords do not match. Please re-enter the password correctly.')
        else:
            st.warning('Please enter a username, password, and email.')


# Show customer requests
def show_customer_requests():
    st.header('Customer Requests')


    # Fetch pickup data from the database
    c.execute("SELECT * FROM pickup_laundary_data")
    rows = c.fetchall()

    # Convert rows to dataframe
    pickup_data = pd.DataFrame(rows, columns=['ID', 'Name', 'Phone', 'Email', 'Pickup Date', 'Pickup Time', 'Status',
                                              'Address', 'City', 'Postal_Code'])
    st.dataframe(pickup_data)


def calculate_dau(pickup_data):
    # Calculate DAU based on pickup data
    dau_data = pickup_data.groupby('Pickup Date')['Phone'].nunique().reset_index(name='DAU')
    dau_data['Pickup Date'] = pd.to_datetime(dau_data['Pickup Date'])
    dau_data = dau_data.set_index('Pickup Date')
    dau_data = dau_data.resample('D').sum()
    return dau_data


# Show sales dashboard
def show_sales_dashboard():

    st.header('Sales Dashboard')

    # Fetch pickup data from the database
    c.execute("SELECT * FROM pickup_laundary_data")
    rows = c.fetchall()

    # Convert rows to dataframe
    pickup_data = pd.DataFrame(rows, columns=['ID', 'Name', 'Phone', 'Email', 'Pickup Date', 'Pickup Time', 'Status',
                                              'Address',  'City','Postal_Code'])

    # Convert 'Pickup Date' column to datetime
    pickup_data['Pickup Date'] = pd.to_datetime(pickup_data['Pickup Date'])

    # Add 'Month' column to the dataframe
    pickup_data['Month'] = pickup_data['Pickup Date'].dt.to_period('M')

    # Group pickup data by month and calculate total sales
    sales_data = pickup_data.groupby('Month').size().reset_index(name='Total Sales')

    # Convert Period object to string representation
    sales_data['Month'] = sales_data['Month'].astype(str)

    # Group registration data by month and calculate new user count
    registration_data = pickup_data.groupby('Month')['Phone'].nunique().reset_index(name='New User Count')

    # Convert Period object to string representation
    registration_data['Month'] = registration_data['Month'].astype(str)

    # Create subplots
    fig = sp.make_subplots(rows=1, cols=3, subplot_titles=('Sales by City', 'Monthly Sales', 'DAU/MAU Ratio'))

    # Sales by City
    city_sales_data = pickup_data.groupby('City').size().reset_index(name='Sales by City')
    fig.add_trace(go.Bar(x=city_sales_data['City'], y=city_sales_data['Sales by City'], name='Sales by City',
                         marker_color='lightskyblue'), row=1, col=1)

    # Monthly Sales
    fig.add_trace(go.Bar(x=sales_data['Month'], y=sales_data['Total Sales'], name='Monthly Sales',
                         marker_color='mediumaquamarine'), row=1, col=2)

    # Calculate the DAU and MAU
    dau_data = calculate_dau(pickup_data)
    mau_data = pickup_data.groupby('Month')['Phone'].nunique()

    # Convert Period object to string representation
    dau_data['Date'] = dau_data.index.strftime('%Y-%m-%d')
    mau_data['Month'] = mau_data.index.strftime('%Y-%m')

    # DAU
    fig.add_trace(go.Scatter(x=dau_data['Date'], y=dau_data['DAU'], name='DAU',
                             mode='lines+markers', line=dict(color='salmon', width=2),
                             marker=dict(color='salmon', size=8)), row=1, col=3)

    # MAU
    fig.add_trace(go.Scatter(x=mau_data['Month'], y=mau_data, name='MAU',
                             mode='lines+markers', line=dict(color='royalblue', width=2),
                             marker=dict(color='royalblue', size=8)), row=1, col=3)

    # Update layout
    fig.update_layout(showlegend=False, height=500, width=900)
    fig.update_yaxes(title_text='Count', row=1, col=1)
    fig.update_yaxes(title_text='Count', row=1, col=2)
    fig.update_yaxes(title_text='Count', row=1, col=3)

    # Set chart titles
    fig.update_xaxes(title_text='City', row=1, col=1)
    fig.update_xaxes(title_text='Month', row=1, col=2)
    fig.update_xaxes(title_text='Date', row=1, col=3)

    # Set chart colors
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')

    # Set font style
    font_family = 'Arial'
    fig.update_layout(font=dict(family=font_family, size=12, color='black'))

    # Set axis label style
    fig.update_layout(xaxis=dict(tickfont=dict(family=font_family, size=10, color='black')),
                      yaxis=dict(tickfont=dict(family=font_family, size=10, color='black')))

    # Set legend style
    fig.update_layout(legend=dict(font=dict(family=font_family, size=10, color='black')))

    # Set title style
    fig.update_layout(title=dict(font=dict(family=font_family, size=16, color='black')))

    # Display the chart
    st.plotly_chart(fig)

    # Fetch pickup data from the database
    c.execute("SELECT * FROM pickup_laundary_data")
    rows = c.fetchall()

    # Convert rows to dataframe
    pickup_data = pd.DataFrame(rows, columns=['ID', 'Name', 'Phone', 'Email', 'Pickup Date', 'Pickup Time', 'Status',
                                              'Address', 'Postal_Code', 'City'])

    # Convert 'Pickup Date' column to datetime
    pickup_data['Pickup Date'] = pd.to_datetime(pickup_data['Pickup Date'])

    # Add 'Month' column to the dataframe
    pickup_data['Month'] = pickup_data['Pickup Date'].dt.to_period('M')

    # Group pickup data by month and calculate total sales
    sales_data = pickup_data.groupby('Month').size().reset_index(name='Total Sales')

    # Convert Period object to string representation
    sales_data['Month'] = sales_data['Month'].astype(str)

    # Group registration data by month and calculate new user count
    registration_data = pickup_data.groupby('Month')['Phone'].nunique().reset_index(name='New User Count')

    # Convert Period object to string representation
    registration_data['Month'] = registration_data['Month'].astype(str)

    # Create subplots
    fig = sp.make_subplots(rows=1, cols=2, subplot_titles=('DAU (Daily Active Users)', 'MAU (Monthly Active Users)'))

    # Calculate the DAU and MAU
    dau_data = calculate_dau(pickup_data)
    mau_data = pickup_data.groupby('Month')['Phone'].nunique()

    # Convert Period object to string representation
    dau_data['Date'] = dau_data.index.strftime('%Y-%m-%d')
    mau_data['Month'] = mau_data.index.strftime('%Y-%m')

    # DAU
    fig.add_trace(go.Scatter(x=dau_data['Date'], y=dau_data['DAU'], name='DAU',
                             mode='lines+markers', line=dict(color='salmon', width=2),
                             marker=dict(color='salmon', size=8)), row=1, col=1)

    # MAU
    fig.add_trace(go.Scatter(x=mau_data['Month'], y=mau_data, name='MAU',
                             mode='lines+markers', line=dict(color='royalblue', width=2),
                             marker=dict(color='royalblue', size=8)), row=1, col=2)

    # Update layout
    fig.update_layout(showlegend=False, height=500, width=900)
    fig.update_yaxes(title_text='Count', row=1, col=1)
    fig.update_yaxes(title_text='Count', row=1, col=2)

    # Set chart titles
    fig.update_xaxes(title_text='Date', row=1, col=1)
    fig.update_xaxes(title_text='Month', row=1, col=2)

    # Set chart colors
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')

    # Set font style
    font_family = 'Arial'
    fig.update_layout(font=dict(family=font_family, size=12, color='black'))

    # Set axis label style
    fig.update_layout(xaxis=dict(tickfont=dict(family=font_family, size=10, color='black')),
                      yaxis=dict(tickfont=dict(family=font_family, size=10, color='black')))

    # Set legend style
    fig.update_layout(legend=dict(font=dict(family=font_family, size=10, color='black')))

    # Set title style
    fig.update_layout(title=dict(font=dict(family=font_family, size=16, color='black')))

    # Display the chart
    st.plotly_chart(fig)



    # Fetch registration data from the database
    c.execute("SELECT * FROM users")
    registration_rows = c.fetchall()
    registration_data = pd.DataFrame(registration_rows, columns=['ID', 'Username', 'Password', 'Email', 'Date'])

    # Group the registration data by month and calculate the count of new users
    registration_data['Month'] = pd.to_datetime(registration_data['Date']).dt.to_period('M')
    new_user_count = registration_data.groupby('Month').size().reset_index(name='New User Count')

    # Convert the 'Month' column to string for plotting
    new_user_count['Month'] = new_user_count['Month'].astype(str)

    # Create a line graph using the new user count data
    fig, ax = plt.subplots()
    ax.plot(new_user_count['Month'], new_user_count['New User Count'], marker='o')
    ax.set_xlabel('Month')
    ax.set_ylabel('New User Count')
    ax.set_title('Growth Chart')

    # Rotate x-axis labels for better visibility
    plt.xticks(rotation=45)

    # Display the line graph
    st.pyplot(fig)

    # Display the metrics table
    st.subheader('Metrics')
    st.write(sales_data)


# Show customer ledger
def show_customer_ledger():
    st.header('Customer Ledger')

    # Fetch customer data from the database
    c.execute("SELECT * FROM pickup_laundary_data")
    rows = c.fetchall()

    # Convert rows to dataframe
    customer_data = pd.DataFrame(rows, columns=['ID', 'Name', 'Phone', 'Email', 'Pickup Date', 'Pickup Time', 'Status',
                                                'Address', 'Postal_Code', 'City'])

    # Select customer by name
    selected_customer = st.selectbox('Select Customer', customer_data['Name'])

    # Fetch ledger entries for the selected customer
    c.execute("SELECT * FROM ledger WHERE Customer_ID=?",
              (customer_data.loc[customer_data['Name'] == selected_customer, 'ID'].values[0],))
    ledger_rows = c.fetchall()

    # Convert ledger rows to dataframe
    ledger_data = pd.DataFrame(ledger_rows, columns=['ID', 'Customer ID', 'Date', 'Description', 'Amount'])

    # Display the ledger data in a table
    st.dataframe(ledger_data)

    # Add new ledger entry
    st.subheader('Add New Ledger Entry')
    date = st.date_input('Date', key='new_ledger_date')
    description = st.text_input('Description')
    amount = st.number_input('Amount')
    add_ledger_button = st.button('Add Ledger Entry')

    # Handle add ledger button click event
    if add_ledger_button:
        if selected_customer and date and description and amount:
            # Insert the new ledger entry into the database
            c.execute("INSERT INTO ledger (Customer_ID, Date, Description, Amount) VALUES (?, ?, ?, ?)",
                      (customer_data.loc[customer_data['Name'] == selected_customer, 'ID'].values[0], date, description,
                       amount))
            conn.commit()
            st.success('Ledger entry added successfully!')
        else:
            st.warning('Please fill in all the fields.')

    # Remove ledger entry
    st.subheader('Remove Ledger Entry')
    selected_ledger_id = st.text_input("Enter Ledger ID to Remove")
    remove_button = st.button('Remove Entry')

    # Handle remove button click event
    if remove_button and selected_ledger_id:
        # Fetch the selected ledger entry from the database
        c.execute("SELECT * FROM ledger WHERE ID=?", (selected_ledger_id,))
        selected_entry = c.fetchone()

        if selected_entry:
            # Delete the selected ledger entry from the database
            c.execute("DELETE FROM ledger WHERE ID=?", (selected_ledger_id,))
            conn.commit()
            st.success('Ledger entry removed successfully!')
        else:
            st.warning("Invalid Ledger ID.")


# ...


# Show admin dashboard
def show_admin_dashboard():
    st.header('Admin Dashboard')

    # Input form for adding new pickup data
    st.subheader('Add New Pickup Data')
    name = st.text_input('Name')
    phone = st.text_input('Phone')
    email = st.text_input('Email')
    pickup_date = st.date_input('Pickup Date')
    pickup_time = st.time_input('Pickup Time')
    status = st.selectbox('Status', ['Pending', 'Completed'])
    address = st.text_input('Address')
    city = st.text_input('City')
    postal_code = st.text_input('Postal Code')
    item_names = st.text_input('Item Names (comma-separated)')
    item_prices = st.text_input('Item Prices (comma-separated)')  # Input field for item prices
    add_button = st.button('Add Pickup Data')

    # Handle add button click event
    if add_button:
        # Convert pickup_date to string in 'YYYY-MM-DD' format
        pickup_date_str = pickup_date.strftime('%Y-%m-%d')

        # Convert pickup_time to string in 'HH:MM:SS' format
        pickup_time_str = pickup_time.strftime('%H:%M:%S')

        # Insert pickup data into the database
        c.execute(
            "INSERT INTO pickup_laundary_data (Name, Phone, Email, Pickup_Date, Pickup_Time, Status, Address, City, Postal_Code) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (name, phone, email, pickup_date_str, pickup_time_str, status, address, city, postal_code))
        conn.commit()

        # Retrieve the ID of the inserted pickup data
        pickup_id = c.lastrowid

        # Insert item data into the database
        item_names_list = item_names.split(',')
        item_prices_list = item_prices.split(',')
        for item_name, item_price in zip(item_names_list, item_prices_list):
            c.execute("INSERT INTO order_items (Pickup_ID, Item_Name,Item_Price) VALUES (?, ?,?)",
                      (pickup_id, item_name.strip(), item_price.strip()))

            conn.commit()

        conn.commit()

        st.success('Pickup data added successfully!')
    # Delete a record
    delete_order_id = st.text_input("Enter Order ID to Delete")
    delete_button = st.button('Delete Record')

    # Handle delete button click event
    if delete_button:
        if delete_order_id:
            # Check if the order ID exists in the database
            c.execute("SELECT * FROM pickup_laundary_data WHERE ID=?", (delete_order_id,))
            result = c.fetchone()

            if result:
                # Delete the record from pickup_laundary_data table
                c.execute("DELETE FROM pickup_laundary_data WHERE ID=?", (delete_order_id,))
                conn.commit()

                # Delete the related records from order_items table
                c.execute("DELETE FROM order_items WHERE Pickup_ID=?", (delete_order_id,))
                conn.commit()

                st.success('Record deleted successfully!')
            else:
                st.warning("Invalid Order ID.")
        else:
            st.warning("Please enter an Order ID.")

    # Filter by status
    status_filter = st.selectbox('Filter by Status', ['All', 'Pending', 'Completed'])  # Filter by status
    if status_filter == 'All':
        c.execute(
            "SELECT pickup_laundary_data.*, order_items.Item_Name, order_items.Item_Price FROM pickup_laundary_data LEFT JOIN order_items ON pickup_laundary_data.id = order_items.Pickup_ID"
        )
    else:
        c.execute(
            "SELECT p.*, o.Item_Name, o.Item_Price FROM pickup_laundary_data p "
            "LEFT JOIN order_items o ON p.id = o.Pickup_ID WHERE p.Status=?",
            (status_filter,)
        )

    rows = c.fetchall()
    admin_data = pd.DataFrame(
        rows,
        columns=[
            'ID',
            'Name',
            'Phone',
            'Email',
            'Pickup Date',
            'Pickup Time',
            'Status',
            'Address',
            'Postal_Code',
            'City',
            'Item_Name',
            'Item_Price',
        ],
    )

    # Display the filtered data in a table
    st.subheader('Filtered Data')
    st.dataframe(admin_data)

    # Update status to "Completed"
    selected_order_id = st.text_input("Enter Order ID to Mark as Completed")
    update_button = st.button('Update Status to Completed')

    # Handle update button click event
    if update_button:
        if selected_order_id:
            # Check if the order ID is valid and the status is not already "Completed"
            selected_order_status = admin_data.loc[admin_data['ID'] == int(selected_order_id), 'Status'].values

            if len(selected_order_status) > 0 and selected_order_status[0] != "Completed":
                # Update the status to "Completed" in the database
                c.execute("UPDATE pickup_laundary_data SET Status=? WHERE ID=?", ("Completed", selected_order_id))
                conn.commit()
                st.success('Pickup status updated to "Completed".')
            else:
                st.warning("Invalid Order ID or Order already marked as Completed.")
        else:
            st.warning("Please enter an Order ID.")

    # Fetch pickup data from the database
    c.execute("SELECT id,Username,Email,Date FROM users")
    rows = c.fetchall()

    # Create a filter to display registered users
    registered_users = st.checkbox('Display Registered Users')

    if registered_users:
        # Convert rows to dataframe
        registered_users_data = pd.DataFrame(rows,
                                             columns=['id', 'Username', 'Email', 'Date'])

        # Display the filtered pickup data
        st.subheader('Pickup Data')
        st.write(registered_users_data)

    # Data aggregation and export
    st.subheader('Data Aggregation and Export')
    aggregation_type = st.selectbox('Aggregation Type', ['Total', 'Count'])
    if aggregation_type == 'Total':
        total_pickups = admin_data.shape[0]
        st.write(f'Total Pickups: {total_pickups}')
    elif aggregation_type == 'Count':
        status_count = admin_data['Status'].value_counts()
        st.write(status_count)

    export_button = st.button('Export Data')
    if export_button:
        admin_data.to_csv('admin_data.csv', index=False)
        st.success('Data exported successfully!')

    # Data Analytics
    st.subheader('Data Analytics')

    if not admin_data['Item_Price'].empty:
        # Bar chart of pickups by status using Seaborn
        st.subheader('Bar chart of pickups by status')
        sns.set_theme(style='darkgrid')
        plt.figure(figsize=(8, 6))
        sns.countplot(data=admin_data, x='Status')
        st.pyplot()
    if not admin_data['Item_Price'].empty:
        # Bar chart of pickups by status using Plotly
        st.subheader('Bar chart of pickups by status (Plotly)')
        status_count_plotly = admin_data['Status'].value_counts().reset_index()
        status_count_plotly.columns = ['Status', 'Count']
        fig = px.bar(status_count_plotly, x='Status', y='Count')
        st.plotly_chart(fig)

    # Check if there are values in the Item_Price column
    if not admin_data['Item_Price'].empty:
        # Histogram of pickup prices using Altair
        st.subheader('Histogram of pickup prices')
        chart_data = alt.Chart(admin_data).mark_bar().encode(
            alt.X('Item_Price', bin=True),
            y='count()',
        ).properties(
            width=600,
            height=400
        )
        st.altair_chart(chart_data)
    else:
        st.warning('No pickup prices available.')


# Deregister User
def deregister_user():
    st.header('Deregister User')

    # Input field for email
    email = st.text_input('Enter User Email')

    if email:
        # Fetch the user from the database based on the entered email
        c.execute("SELECT * FROM users WHERE Email=?", (email,))
        selected_user_row = c.fetchone()

        if selected_user_row:
            user_id = selected_user_row[0]
            username = selected_user_row[1]
            email = selected_user_row[3]
            date = selected_user_row[4]

            st.subheader('User Details')
            st.write('Username:', username)
            st.write('Email:', email)
            st.write('Date:', date)

            deregister_button = st.button('Deregister User')

            # Handle deregister button click event
            if deregister_button:
                # Delete the selected user from the database
                c.execute("DELETE FROM users WHERE ID=?", (user_id,))
                conn.commit()
                st.success('User deregistered successfully!')
        else:
            st.warning('User not found.')
    else:
        st.info('Enter the user email to deregister.')


# Run the app
if __name__ == '__main__':
    main()
