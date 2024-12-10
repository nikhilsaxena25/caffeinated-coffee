import streamlit as st
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, ForeignKey, text
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import datetime
import pandas as pd

# Database setup with SERIALIZABLE isolation level
engine = create_engine('sqlite:///caffeinated.db', isolation_level="SERIALIZABLE")
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

# Database Models
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

# Indexes for Optimization
session.execute(text("CREATE INDEX IF NOT EXISTS idx_order_date ON Orders(order_date);")) # Optimizes queries that filter or sort orders based on their date.
session.execute(text("CREATE INDEX IF NOT EXISTS idx_stock_quantity ON CoffeeBeans(stock_quantity);")) # Speeds up queries that filter coffee beans based on their stock.
session.execute(text("CREATE INDEX IF NOT EXISTS idx_user_id ON Orders(user_id);")) # Enhances queries that filter orders based on a specific user.
session.execute(text("CREATE INDEX IF NOT EXISTS idx_status ON Orders(status);")) # Speeds up queries that filter orders based on their current status.

# Streamlit UI
st.set_page_config(page_title="Caffeinated", page_icon="☕", layout="wide")
st.title("☕ Welcome to Caffeinated Coffee ☕")

# Ensure Default User
def ensure_user_exists():
    user = session.query(User).filter_by(user_id=1).first()
    if not user:
        new_user = User(user_id=1, name="Default User", email="user@example.com")
        session.add(new_user)
        session.commit()

# Function to load demo coffee beans and orders
def load_demo_data_and_orders():
    try:
        # Demo coffee bean data
        demo_beans = [
            {"name": "Arabica", "origin": "Brazil", "roast_level": "Medium", "price_per_gram": 0.05, "stock_quantity": 1000},
            {"name": "Robusta", "origin": "Vietnam", "roast_level": "Dark", "price_per_gram": 0.03, "stock_quantity": 500},
            {"name": "Blue Mountain", "origin": "Jamaica", "roast_level": "Light", "price_per_gram": 0.10, "stock_quantity": 200},
            {"name": "Ethiopian Yirgacheffe", "origin": "Ethiopia", "roast_level": "Medium", "price_per_gram": 0.08, "stock_quantity": 300},
            {"name": "Colombian Supremo", "origin": "Colombia", "roast_level": "Dark", "price_per_gram": 0.07, "stock_quantity": 800},
        ]

        # Ensure the default user exists
        ensure_user_exists()

        # Add coffee beans
        for bean in demo_beans:
            new_bean = CoffeeBean(**bean)
            session.add(new_bean)
        session.flush()  # Flush to generate bean IDs for order creation

        # Fetch all added beans
        beans = session.query(CoffeeBean).all()

        # Demo order data (order quantities and statuses)
        demo_orders = [
            {"bean_id": beans[0].bean_id, "quantity": 50, "status": "Pending"},
            {"bean_id": beans[1].bean_id, "quantity": 100, "status": "Shipped"},
            {"bean_id": beans[2].bean_id, "quantity": 25, "status": "Delivered"},
            {"bean_id": beans[3].bean_id, "quantity": 10, "status": "Pending"},
            {"bean_id": beans[4].bean_id, "quantity": 75, "status": "Shipped"},
        ]

        # Add orders and reduce stock
        for order_data in demo_orders:
            # Calculate total price
            bean = session.query(CoffeeBean).filter_by(bean_id=order_data["bean_id"]).first()
            total_price = bean.price_per_gram * order_data["quantity"]

            # Create a new order
            new_order = Order(
                user_id=1,  # Default user
                total_price=total_price,
                status=order_data["status"],
            )
            session.add(new_order)
            session.flush()  # Get the order ID for the order item

            # Create an order item
            new_order_item = OrderItem(
                order_id=new_order.order_id,
                bean_id=bean.bean_id,
                quantity=order_data["quantity"],
                price=total_price,
            )
            session.add(new_order_item)

            # Update bean stock
            bean.stock_quantity -= order_data["quantity"]

        session.commit()
        st.success("Demo coffee beans and orders loaded successfully!")
        st.rerun()
    except Exception as e:
        session.rollback()
        st.error(f"Error loading demo data and orders: {e}")

# Reset Data
def reset_all_data():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    ensure_user_exists()
    st.rerun()
    st.success("Database reset completed!")

# Sidebar with Reset and Demo Data Buttons
with st.sidebar:
    if st.button("🔄 Reset All Data"):
        reset_all_data()

    if st.button("📥 Load Demo Data (reset all data before!)"):
        load_demo_data_and_orders()


# Add Coffee Bean
def add_coffee_bean():
    st.header("Add a New Coffee Bean")
    name = st.text_input("Bean Name")
    origin = st.text_input("Origin")
    roast_level = st.selectbox("Roast Level", ["Light", "Medium", "Dark"])
    price_per_gram = st.number_input("Price per Gram ($)", min_value=0.01, step=0.01)
    stock_quantity = st.number_input("Stock Quantity (grams)", min_value=1, step=1)

    if st.button("Add Coffee Bean"):
        try:
            new_bean = CoffeeBean(
                name=name, origin=origin, roast_level=roast_level,
                price_per_gram=price_per_gram, stock_quantity=stock_quantity
            )
            session.add(new_bean)
            session.commit()
            st.success(f"Coffee bean '{name}' added!")
            st.rerun()
        except Exception as e:
            session.rollback()
            st.error(f"Error adding coffee bean: {e}")

# Update Coffee Bean
def update_coffee_bean():
    st.header("Update Coffee Bean Details")
    beans = session.query(CoffeeBean).all()
    if beans:
        bean_names = [bean.name for bean in beans]
        selected_bean_name = st.selectbox("Select Coffee Bean", bean_names, key="update_coffee_bean_select")

        selected_bean = session.query(CoffeeBean).filter_by(name=selected_bean_name).first()
        if selected_bean:
            new_name = st.text_input("New Name", value=selected_bean.name)
            new_origin = st.text_input("New Origin", value=selected_bean.origin)
            new_roast_level = st.selectbox("New Roast Level", ["Light", "Medium", "Dark"], index=["Light", "Medium", "Dark"].index(selected_bean.roast_level))
            new_price = st.number_input("New Price per Gram ($)", min_value=0.01, value=selected_bean.price_per_gram)
            new_stock = st.number_input("New Stock Quantity", min_value=0, value=selected_bean.stock_quantity)

            if st.button("Update Coffee Bean"):
                try:
                    selected_bean.name = new_name
                    selected_bean.origin = new_origin
                    selected_bean.roast_level = new_roast_level
                    selected_bean.price_per_gram = new_price
                    selected_bean.stock_quantity = new_stock
                    session.commit()
                    st.success(f"Coffee bean '{new_name}' updated!")
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Error updating coffee bean: {e}")

# Delete Coffee Bean
def delete_coffee_bean():
    st.header("Delete a Coffee Bean")
    beans = session.query(CoffeeBean).all()
    if beans:
        bean_names = [bean.name for bean in beans]
        selected_bean_name = st.selectbox("Select Coffee Bean", bean_names, key="delete_coffee_bean_select")

        if st.button("Delete Coffee Bean"):
            try:
                selected_bean = session.query(CoffeeBean).filter_by(name=selected_bean_name).first()
                session.delete(selected_bean)
                session.commit()
                st.success(f"Coffee bean '{selected_bean_name}' deleted!")
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"Error deleting coffee bean: {e}")

# View Available Coffee Beans
def view_available_beans():
    st.header("Available Coffee Beans")
    
    # Query to fetch available beans with their stock
    available_beans_query = text("""
        SELECT name, origin, roast_level, price_per_gram, stock_quantity
        FROM CoffeeBeans
        WHERE stock_quantity > 0
        ORDER BY stock_quantity DESC;
    """)
    available_beans = session.execute(available_beans_query).fetchall()
    
    # Display the beans in a table
    if available_beans:
        st.table([{
            "Name": bean.name,
            "Origin": bean.origin,
            "Roast Level": bean.roast_level,
            "Price per Gram": f"${bean.price_per_gram:.2f}",
            "Stock Quantity": f"{bean.stock_quantity} grams"
        } for bean in available_beans])
    else:
        st.write("No coffee beans are currently available in stock.")

# Place Order
def place_order():
    st.header("Place an Order")
    ensure_user_exists()

    # Fetch all coffee beans
    beans = session.query(CoffeeBean).all()

    if beans:
        # Create a list of available coffee bean names
        bean_names = [bean.name for bean in beans]
        selected_bean_name = st.selectbox("Choose Coffee Bean", options=bean_names)

        # Fetch the selected bean's details
        selected_bean = session.query(CoffeeBean).filter_by(name=selected_bean_name).first()

        if selected_bean:
            # Display bean details
            st.write(f"**Origin**: {selected_bean.origin}")
            st.write(f"**Roast Level**: {selected_bean.roast_level}")
            st.write(f"**Price per Gram**: ${selected_bean.price_per_gram:.2f}")
            st.write(f"**Available Stock**: {selected_bean.stock_quantity} grams")

            # Ensure stock is greater than 0 before allowing order placement
            if selected_bean.stock_quantity > 0:
                # Input for quantity
                max_quantity = selected_bean.stock_quantity  # Max quantity for the order
                quantity = st.number_input(
                    f"Select quantity for {selected_bean.name}",
                    min_value=1,
                    max_value=max_quantity, 
                    step=1
                )

                # Button to place the order
                if st.button("Place Order"):
                    total_price = selected_bean.price_per_gram * quantity

                    try:
                        # use of transaction for placing order
                        with session.begin_nested():
                            # Check stock before proceeding
                            if selected_bean.stock_quantity < quantity:
                                st.error("Insufficient stock for this coffee bean.")
                                return

                            # Update stock and create order
                            selected_bean.stock_quantity -= quantity
                            new_order = Order(
                                user_id=1,
                                total_price=total_price,
                                status="Pending"
                            )
                            session.add(new_order)
                            session.flush()  # Ensure new_order.order_id is generated

                            order_item = OrderItem(
                                order_id=new_order.order_id,
                                bean_id=selected_bean.bean_id,
                                quantity=quantity,
                                price=total_price
                            )
                            session.add(order_item)

                        # Commit the transaction
                        session.commit()
                        st.success(f"Order placed for {quantity} grams of {selected_bean.name}! Remaining stock: {selected_bean.stock_quantity} grams.")
                        st.rerun()
                    except Exception as e:
                        # Roll back in case of error
                        session.rollback()
                        st.error(f"Error placing order: {str(e)}")
            else:
                st.write("The selected coffee bean is out of stock.")
    else:
        st.write("No coffee beans available for ordering.")

# Delete Order
def delete_order():
    st.header("Delete an Order")
    orders = session.query(Order).all()
    if orders:
        order_ids = [order.order_id for order in orders]
        selected_order_id = st.selectbox("Select Order ID", order_ids)

        if st.button("Delete Order"):
            try:
                order_to_delete = session.query(Order).filter_by(order_id=selected_order_id).first()
                session.delete(order_to_delete)
                session.commit()
                st.success(f"Order ID '{selected_order_id}' deleted!")
            except Exception as e:
                session.rollback()
                st.error(f"Error deleting order: {e}")

# View All Orders with Bean Details
def view_orders():
    st.header("All Orders with Coffee Bean Details")

    # Query to fetch orders with user, bean, and order details
    orders_query = text("""
        SELECT 
            Orders.order_id,
            Users.name AS user_name,
            Orders.status,
            Orders.total_price,
            Orders.order_date,
            CoffeeBeans.name AS bean_name,
            CoffeeBeans.origin,
            CoffeeBeans.roast_level,
            OrderItems.quantity
        FROM Orders
        JOIN Users ON Orders.user_id = Users.user_id
        JOIN OrderItems ON Orders.order_id = OrderItems.order_id
        JOIN CoffeeBeans ON OrderItems.bean_id = CoffeeBeans.bean_id
        ORDER BY Orders.order_date DESC
    """)
    orders = session.execute(orders_query).fetchall()

    # List to store the final data
    orders_data = []

    for order in orders:
        orders_data.append({
            "Order ID": order.order_id,
            "User": order.user_name,
            "Status": order.status,
            "Total Price": f"${order.total_price:.2f}",
            "Order Date": order.order_date.strftime("%Y-%m-%d") if isinstance(order.order_date, datetime) else order.order_date,
            "Bean Name": order.bean_name,
            "Origin": order.origin,
            "Roast Level": order.roast_level,
            "Quantity (grams)": order.quantity
        })

    if orders_data:
        orders_df = pd.DataFrame(orders_data)
        st.dataframe(orders_df, hide_index=True)
    else:
        st.write("No orders available.")

# Change Status of an Order
def update_order_status():
    st.header("Update Order Status")

    # Fetch all orders from the database
    orders = session.query(Order).all()

    if orders:
        for order in orders:
            st.write(f"Order ID: {order.order_id} - Current Status: {order.status}")

            # Dropdown to select the new status
            new_status = st.selectbox(
                f"Update Status for Order {order.order_id}",
                ["Pending", "Shipped", "Delivered"],
                index=["Pending", "Shipped", "Delivered"].index(order.status),
                key=f"status_{order.order_id}"
            )

            # Button to apply the status update
            if st.button(f"Update Status", key=f"update_status_{order.order_id}"):
                try:
                    # Fetch the order again to ensure consistency
                    order_to_update = session.query(Order).filter_by(order_id=order.order_id).first()

                    # Only update if the status has changed
                    if order_to_update and new_status != order_to_update.status:
                        order_to_update.status = new_status
                        session.commit()  # Commit the transaction
                        st.success(f"Updated status for Order {order.order_id} to {new_status}")
                        st.rerun()  # Refresh the UI to reflect changes
                    else:
                        st.info(f"No changes made for Order {order.order_id}.")
                except Exception as e:
                    session.rollback()  # Roll back the transaction in case of errors
                    st.error(f"Error updating order status: {str(e)}")
    else:
        st.write("No orders available to update.")

# Tabs for Layout
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Add Coffee Bean", "Update Coffee Bean", "Delete Coffee Bean", "View available beans",
    "Place Order", "Delete Order", "View Orders", "Change Status"
])

with tab1:
    add_coffee_bean()
with tab2:
    update_coffee_bean()
with tab3:
    delete_coffee_bean()
with tab4:
    view_available_beans()
with tab5:
    place_order()
with tab6:
    delete_order()
with tab7:
    view_orders()
with tab8:
    update_order_status()

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