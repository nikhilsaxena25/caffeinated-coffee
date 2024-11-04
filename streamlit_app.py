import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime

# Database setup
engine = create_engine('sqlite:///caffeinated.db')
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# Database
class User(Base):
    __tablename__ = 'Users'
    user_id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String)

class CoffeeBean(Base):
    __tablename__ = 'CoffeeBeans'
    bean_id = Column(Integer, primary_key=True)
    name = Column(String)
    origin = Column(String)
    roast_level = Column(String)
    price_per_gram = Column(Float)
    stock_quantity = Column(Integer)

class Order(Base):
    __tablename__ = 'Orders'
    order_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('Users.user_id'))
    total_price = Column(Float)
    order_date = Column(Date, default=datetime.now)
    status = Column(String)
    user = relationship("User", back_populates="orders")

User.orders = relationship("Order", back_populates="user")

class OrderItem(Base):
    __tablename__ = 'OrderItems'
    item_id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('Orders.order_id'))
    bean_id = Column(Integer, ForeignKey('CoffeeBeans.bean_id'))
    quantity = Column(Integer)
    price = Column(Float)
    order = relationship("Order", back_populates="items")
    bean = relationship("CoffeeBean")

Order.items = relationship("OrderItem", back_populates="order")
Base.metadata.create_all(engine)

# Streamlit setup
st.set_page_config(page_title="Caffeinated", page_icon="☕", layout="wide")
st.title("☕ Welcome to Caffeinated Coffee ☕")

# Ensure a default user exists as placeholder
def ensure_user_exists():
    user = session.query(User).filter_by(user_id=1).first()
    if not user:
        new_user = User(user_id=1, name=":D User", email="user@example.com")
        session.add(new_user)
        session.commit()

# Reset all data (both database and session state)
def reset_all_data():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    ensure_user_exists()  # Ensure user exists after reset
    st.success("All data has been reset!")

# Sidebar Reset Button
with st.sidebar:
    if st.button("🔄 Reset All Data"):
        reset_all_data()

# Section 1: Add a New Coffee Bean
def add_coffee_bean():
    st.header("Add a New Coffee Bean")
    name = st.text_input("Bean Name")
    origin = st.text_input("Origin")
    roast_level = st.selectbox("Roast Level", options=["Light", "Medium", "Dark"])
    price_per_gram = st.number_input("Price per Gram ($)", min_value=0.01, step=0.01)
    stock_quantity = st.number_input("Stock Quantity (grams)", min_value=1, step=1)
    
    if st.button("Add Coffee Bean"):
        new_bean = CoffeeBean(
            name=name,
            origin=origin,
            roast_level=roast_level,
            price_per_gram=price_per_gram,
            stock_quantity=stock_quantity
        )
        session.add(new_bean)
        session.commit()
        st.success(f"Added '{name}' to the coffee beans list!")
        st.rerun()

# Section 2: Place an Order
def place_order():
    st.header("Place an Order")
    ensure_user_exists()
    
    beans = session.query(CoffeeBean).all()
    if beans:
        bean_names = [bean.name for bean in beans]
        selected_bean = st.selectbox("Choose Coffee Bean", options=bean_names)
        selected_bean_obj = session.query(CoffeeBean).filter_by(name=selected_bean).first()
        
        if selected_bean_obj and selected_bean_obj.stock_quantity > 0:
            quantity = st.number_input(
                f"Select quantity for {selected_bean}",
                min_value=1,
                max_value=selected_bean_obj.stock_quantity,
                step=1
            )
            
            if st.button("Place Order"):
                total_price = selected_bean_obj.price_per_gram * quantity
                new_order = Order(
                    user_id=1,
                    total_price=total_price,
                    status="Pending"
                )
                session.add(new_order)
                session.flush()

                order_item = OrderItem(
                    order_id=new_order.order_id,
                    bean_id=selected_bean_obj.bean_id,
                    quantity=quantity,
                    price=total_price
                )
                session.add(order_item)

                selected_bean_obj.stock_quantity -= quantity
                session.commit()

                st.success(f"Order placed for {quantity} grams of {selected_bean}!")
        else:
            st.write("The selected coffee bean is out of stock.")

# Section 3: Low Stock Alert and Restock Function
def low_stock_alert():
    st.header("Low Stock Alert")
    threshold = 10

    low_stock_query = text("""
        SELECT bean_id, name, stock_quantity
        FROM CoffeeBeans
        WHERE stock_quantity < :threshold
    """)
    low_stock_beans = session.execute(low_stock_query, {"threshold": threshold}).fetchall() #select a threshold 

    if low_stock_beans:
        for bean in low_stock_beans:
            st.write(f"Bean: {bean.name} - Stock: {bean.stock_quantity} grams")
            restock_amount = st.number_input(f"Restock amount for {bean.name}", min_value=1, step=1, key=bean.bean_id)
            
            if st.button(f"Restock {bean.name}", key=f"restock_{bean.bean_id}"):
                selected_bean = session.query(CoffeeBean).filter_by(bean_id=bean.bean_id).first()
                if selected_bean:
                    selected_bean.stock_quantity += restock_amount
                    session.commit()
                    st.success(f"Restocked {restock_amount} grams of {bean.name}. New stock: {selected_bean.stock_quantity} grams")
                    st.rerun()
    else:
        st.write("Restocked or All beans have sufficient stock.")

# Section 4: Monthly Sales Report
def monthly_sales_report():
    st.header("Monthly Sales Report")
    
    sales_report_query = text("""
        SELECT strftime('%Y-%m', order_date) AS month, 
               COUNT(order_id) AS total_orders, 
               SUM(total_price) AS total_revenue
        FROM Orders
        GROUP BY month
        ORDER BY month DESC
    """)
    sales_data = session.execute(sales_report_query).fetchall()
    
    if sales_data:
        st.table([{
            "Month": data.month,
            "Total Orders": data.total_orders,
            "Total Revenue": f"${data.total_revenue:.2f}"
        } for data in sales_data])
    else:
        st.write("No sales data available.")

# Section 5: Top-Selling Coffee Beans
def top_selling_beans():
    st.header("Top-Selling Coffee Beans")
    
    top_beans_query = text("""
        SELECT CoffeeBeans.name, SUM(OrderItems.quantity) AS total_sold
        FROM OrderItems
        JOIN CoffeeBeans ON OrderItems.bean_id = CoffeeBeans.bean_id
        GROUP BY CoffeeBeans.bean_id
        ORDER BY total_sold DESC
        LIMIT 5
    """)
    top_beans = session.execute(top_beans_query).fetchall()

    if top_beans:
        st.table([{
            "Bean Name": bean.name,
            "Total Sold (grams)": bean.total_sold
        } for bean in top_beans])
    else:
        st.write("No sales data available.")

# Section 6: Update Order Status
def update_order_status():
    st.header("Update Order Status")

    orders = session.query(Order).all()
    if orders:
        for order in orders:
            st.write(f"Order ID: {order.order_id} - Current Status: {order.status}")
            
            new_status = st.selectbox(
                f"Update Status for Order {order.order_id}", 
                ["Pending", "Shipped", "Delivered"], 
                index=["Pending", "Shipped", "Delivered"].index(order.status), 
                key=f"status_{order.order_id}"
            )
            
            if st.button(f"Update Status", key=f"update_status_{order.order_id}"):
                if new_status != order.status:
                    order.status = new_status
                    session.commit()
                    st.success(f"Updated status for Order {order.order_id} to {new_status}")
                    st.rerun()
    else:
        st.write("No orders available to update.")

# Section 7: View All Orders
def view_orders():
    st.header("All Orders")

    orders_query = text("""
        SELECT Orders.order_id, Users.name AS user_name, Orders.status, Orders.total_price, Orders.order_date
        FROM Orders
        JOIN Users ON Orders.user_id = Users.user_id
        ORDER BY Orders.order_date DESC
    """)
    orders = session.execute(orders_query).fetchall()
    
    orders_data = []
    for order in orders:
        items_query = text("""
            SELECT CoffeeBeans.name AS bean_name, OrderItems.quantity, OrderItems.price
            FROM OrderItems
            JOIN CoffeeBeans ON OrderItems.bean_id = CoffeeBeans.bean_id
            WHERE OrderItems.order_id = :order_id
        """)
        items = session.execute(items_query, {"order_id": order.order_id}).fetchall()
        
        items_list = [f"{item.bean_name}: {item.quantity} grams at ${item.price:.2f}" for item in items]
        items_str = "\n".join(items_list)  # better readablity 

        # datetime -> string
        if isinstance(order.order_date, datetime):
            order_date_str = order.order_date.strftime("%Y-%m-%d")
        else:
            order_date_str = order.order_date
        
        orders_data.append({
            "Order ID": order.order_id,
            "User": order.user_name,
            "Status": order.status,
            "Total Price": f"${order.total_price:.2f}",
            "Order Date": order_date_str,
            "Items": items_str
        })

    st.table(orders_data)

# Section 8: Delete Coffee Bean
def delete_coffee_bean():
    st.header("Delete a Coffee Bean")
    beans = session.query(CoffeeBean).all()
    if beans:
        bean_names = [bean.name for bean in beans]
        selected_bean = st.selectbox("Select Coffee Bean to Delete", options=bean_names)
        
        if st.button("Delete Coffee Bean"):
            bean_to_delete = session.query(CoffeeBean).filter_by(name=selected_bean).first()
            
            if bean_to_delete:
                session.query(OrderItem).filter_by(bean_id=bean_to_delete.bean_id).delete()
                
                # Delete the coffee bean
                session.delete(bean_to_delete)
                session.commit()
                
                st.success(f"Coffee bean '{selected_bean}' and associated items have been deleted.")
                st.rerun()
    else:
        st.write("No coffee beans available to delete.")

# Section 9: Delete Order
def delete_order():
    st.header("Delete an Order")
    orders = session.query(Order).all()
    if orders:
        order_ids = [order.order_id for order in orders]
        selected_order_id = st.selectbox("Select Order ID to Delete", options=order_ids)
        
        if st.button("Delete Order"):
            order_to_delete = session.query(Order).filter_by(order_id=selected_order_id).first()
            
            if order_to_delete:
                session.query(OrderItem).filter_by(order_id=selected_order_id).delete()
                
                # Delete the order
                session.delete(order_to_delete)
                session.commit()
                
                st.success(f"Order ID '{selected_order_id}' and associated items have been deleted.")
                st.rerun()
    else:
        st.write("No orders available to delete.")

# Main Layout with Tabs
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "Add Coffee Bean", "Place Order", "Low Stock Alert", 
    "Monthly Sales Report", "Top-Selling Beans", "Update Order Status", 
    "View Orders", "Delete Coffee Bean", "Delete Order"
])

with tab1:
    add_coffee_bean()
with tab2:
    place_order()
with tab3:
    low_stock_alert()
with tab4:
    monthly_sales_report()
with tab5:
    top_selling_beans()
with tab6:
    update_order_status()
with tab7:
    view_orders()
with tab8:
    delete_coffee_bean()
with tab9:
    delete_order()

# Ensure default user exists on startup
ensure_user_exists()

# Close database session
session.close()

# Footer
st.markdown(
    """
    <style>
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #1c1e21;
        color: #d3d3d3;
        text-align: center;
        padding: 10px;
        font-size: 14px;
    }
    </style>
    <div class="footer">
        Made with love and hard work from Nikhil Saxena
    </div>
    """,
    unsafe_allow_html=True
)
