import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timezone
import numpy as np

st.set_page_config(page_title="Stuck Orders Analysis", layout="wide", page_icon="📊")

st.title("📊 Stuck Orders Analysis Dashboard")
st.markdown("""
This dashboard helps analyze orders that should have moved to `finished` status but are stuck in `eticket_issued` status
even after the travel end date has passed.
""")

# File upload
uploaded_file = st.file_uploader("Upload CSV file with stuck orders", type=['csv'])

if uploaded_file is not None:
    # Load data
    df = pd.read_csv(uploaded_file)

    # Convert timestamp columns (using format='mixed' to handle varying formats)
    timestamp_cols = ['order_created_timestamp', 'travel_start_ts', 'travel_end_ts']

    # Check if new schema columns exist
    if 'account_first_order_created_timestamp' in df.columns:
        timestamp_cols.extend(['account_first_order_created_timestamp', 'account_last_order_created_timestamp'])

    for col in timestamp_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='mixed', utc=True)

    # Calculate metrics
    current_time = datetime.now(timezone.utc)
    df['days_stuck'] = (current_time - df['travel_end_ts']).dt.days
    df['order_to_travel_days'] = (df['travel_start_ts'] - df['order_created_timestamp']).dt.days

    # Calculate days since last order (for churn analysis)
    if 'account_last_order_created_timestamp' in df.columns:
        df['days_since_last_order'] = (current_time - df['account_last_order_created_timestamp']).dt.days

    # Overview metrics
    st.header("📈 Overview")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Stuck Orders", f"{len(df):,}")
    with col2:
        st.metric("Unique Users Affected", f"{df['account_id'].nunique():,}")
    with col3:
        st.metric("Verticals Affected", df['order_type_name'].nunique())
    with col4:
        avg_stuck_days = df['days_stuck'].mean()
        st.metric("Avg Days Stuck", f"{avg_stuck_days:.1f}")

    # Filters
    st.sidebar.header("🔍 Filters")

    # Vertical filter
    all_verticals = sorted(df['order_type_name'].unique())
    selected_verticals = st.sidebar.multiselect(
        "Select Verticals",
        options=all_verticals,
        default=all_verticals
    )

    # Days stuck filter
    max_days = int(df['days_stuck'].max())
    min_days = int(df['days_stuck'].min())
    days_range = st.sidebar.slider(
        "Days Stuck Range",
        min_value=min_days,
        max_value=max_days,
        value=(min_days, max_days)
    )

    # Order status filter (if there are multiple statuses)
    if 'order_status_name' in df.columns:
        all_statuses = sorted(df['order_status_name'].unique())
        selected_statuses = st.sidebar.multiselect(
            "Order Status",
            options=all_statuses,
            default=all_statuses
        )
        filtered_df = df[
            (df['order_type_name'].isin(selected_verticals)) &
            (df['days_stuck'] >= days_range[0]) &
            (df['days_stuck'] <= days_range[1]) &
            (df['order_status_name'].isin(selected_statuses))
        ]
    else:
        filtered_df = df[
            (df['order_type_name'].isin(selected_verticals)) &
            (df['days_stuck'] >= days_range[0]) &
            (df['days_stuck'] <= days_range[1])
        ]

    st.info(f"Showing {len(filtered_df):,} orders after applying filters")

    # Vertical breakdown
    st.header("🎯 Breakdown by Vertical")
    col1, col2 = st.columns(2)

    with col1:
        vertical_counts = filtered_df['order_type_name'].value_counts().reset_index()
        vertical_counts.columns = ['Vertical', 'Count']

        fig_vertical = px.bar(
            vertical_counts,
            x='Vertical',
            y='Count',
            title='Stuck Orders by Vertical',
            color='Count',
            color_continuous_scale='Reds'
        )
        fig_vertical.update_layout(showlegend=False)
        st.plotly_chart(fig_vertical, use_container_width=True)

    with col2:
        fig_pie = px.pie(
            vertical_counts,
            values='Count',
            names='Vertical',
            title='Distribution by Vertical'
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Time analysis
    st.header("⏰ Time Analysis")
    col1, col2 = st.columns(2)

    with col1:
        # Days stuck distribution
        fig_days = px.histogram(
            filtered_df,
            x='days_stuck',
            nbins=50,
            title='Distribution of Days Stuck',
            labels={'days_stuck': 'Days Stuck', 'count': 'Number of Orders'},
            color_discrete_sequence=['#FF6B6B']
        )
        st.plotly_chart(fig_days, use_container_width=True)

    with col2:
        # Days stuck by vertical
        fig_box = px.box(
            filtered_df,
            x='order_type_name',
            y='days_stuck',
            title='Days Stuck by Vertical',
            labels={'order_type_name': 'Vertical', 'days_stuck': 'Days Stuck'},
            color='order_type_name'
        )
        st.plotly_chart(fig_box, use_container_width=True)

    # Order creation timeline
    st.header("📅 Order Creation Timeline")

    timeline_df = filtered_df.groupby([
        pd.Grouper(key='order_created_timestamp', freq='D'),
        'order_type_name'
    ]).size().reset_index(name='count')

    fig_timeline = px.line(
        timeline_df,
        x='order_created_timestamp',
        y='count',
        color='order_type_name',
        title='Orders Created Over Time (by Vertical)',
        labels={'order_created_timestamp': 'Date', 'count': 'Number of Orders'}
    )
    st.plotly_chart(fig_timeline, use_container_width=True)

    # Travel end timeline
    st.header("🏁 Travel End Timeline")

    travel_end_df = filtered_df.groupby([
        pd.Grouper(key='travel_end_ts', freq='D'),
        'order_type_name'
    ]).size().reset_index(name='count')

    fig_travel_end = px.line(
        travel_end_df,
        x='travel_end_ts',
        y='count',
        color='order_type_name',
        title='Travel End Dates Over Time (by Vertical)',
        labels={'travel_end_ts': 'Date', 'count': 'Number of Orders'}
    )
    st.plotly_chart(fig_travel_end, use_container_width=True)

    # User Impact Analysis - Monthly Magnitude
    st.header("👥 User Impact Analysis - Monthly Magnitude")
    st.markdown("""
    This section shows when users first experienced a stuck order based on their travel end date.
    Understanding the monthly growth of newly affected users helps assess the problem's acceleration.
    """)

    # Calculate first stuck order per user
    user_first_impact = filtered_df.groupby('account_id')['travel_end_ts'].min().reset_index()
    user_first_impact.columns = ['account_id', 'first_stuck_order_date']
    user_first_impact['year_month'] = user_first_impact['first_stuck_order_date'].dt.to_period('M')

    # Monthly new users impacted
    monthly_new_users = user_first_impact.groupby('year_month').size().reset_index(name='new_users_impacted')
    monthly_new_users['year_month_str'] = monthly_new_users['year_month'].astype(str)
    monthly_new_users['cumulative_users'] = monthly_new_users['new_users_impacted'].cumsum()

    # Also get total stuck orders per month for comparison
    filtered_df['year_month'] = filtered_df['travel_end_ts'].dt.to_period('M')
    monthly_orders = filtered_df.groupby('year_month').size().reset_index(name='total_stuck_orders')
    monthly_orders['year_month_str'] = monthly_orders['year_month'].astype(str)

    # Merge the data
    monthly_impact = monthly_new_users.merge(monthly_orders, on='year_month_str', how='outer')
    monthly_impact = monthly_impact.sort_values('year_month_str')
    monthly_impact['cumulative_users'] = monthly_impact['new_users_impacted'].cumsum()

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        peak_month = monthly_impact.loc[monthly_impact['new_users_impacted'].idxmax()]
        st.metric("Peak New Users Month", peak_month['year_month_str'])
        st.caption(f"{int(peak_month['new_users_impacted'])} new users")
    with col2:
        avg_new_users = monthly_impact['new_users_impacted'].mean()
        st.metric("Avg New Users/Month", f"{avg_new_users:.0f}")
    with col3:
        last_3_months = monthly_impact.tail(3)['new_users_impacted'].mean()
        st.metric("Avg Last 3 Months", f"{last_3_months:.0f}")
    with col4:
        total_months = len(monthly_impact)
        st.metric("Months Tracked", total_months)

    # Visualization: Cumulative Users Over Time
    st.subheader("📈 Cumulative Unique Users Impacted Over Time")

    fig_cumulative = go.Figure()
    fig_cumulative.add_trace(go.Scatter(
        x=monthly_impact['year_month_str'],
        y=monthly_impact['cumulative_users'],
        mode='lines+markers',
        name='Cumulative Users',
        line=dict(color='#FF6B6B', width=3),
        marker=dict(size=8),
        fill='tozeroy',
        fillcolor='rgba(255, 107, 107, 0.2)'
    ))
    fig_cumulative.update_layout(
        title='Cumulative Unique Users Affected by Stuck Orders',
        xaxis_title='Month',
        yaxis_title='Cumulative Users',
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_cumulative, use_container_width=True)

    # Visualization: New Users per Month
    st.subheader("🆕 New Users Impacted Each Month")

    col1, col2 = st.columns(2)

    with col1:
        fig_new_users = px.bar(
            monthly_impact,
            x='year_month_str',
            y='new_users_impacted',
            title='New Users Experiencing First Stuck Order',
            labels={'year_month_str': 'Month', 'new_users_impacted': 'New Users'},
            color='new_users_impacted',
            color_continuous_scale='Oranges'
        )
        fig_new_users.update_layout(showlegend=False)
        st.plotly_chart(fig_new_users, use_container_width=True)

    with col2:
        fig_dual = go.Figure()
        fig_dual.add_trace(go.Bar(
            x=monthly_impact['year_month_str'],
            y=monthly_impact['new_users_impacted'],
            name='New Users Impacted',
            marker_color='#FF6B6B',
            yaxis='y'
        ))
        fig_dual.add_trace(go.Scatter(
            x=monthly_impact['year_month_str'],
            y=monthly_impact['total_stuck_orders'],
            name='Total Stuck Orders',
            marker_color='#4ECDC4',
            yaxis='y2',
            mode='lines+markers'
        ))
        fig_dual.update_layout(
            title='New Users vs Total Stuck Orders',
            xaxis_title='Month',
            yaxis=dict(title='New Users Impacted', side='left', showgrid=False),
            yaxis2=dict(title='Total Stuck Orders', side='right', overlaying='y', showgrid=False),
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig_dual, use_container_width=True)

    # Total users impacted over time (composition analysis)
    st.subheader("📊 User Composition Over Time: New vs Total Impacted")

    # Calculate total unique users impacted up to each month
    monthly_total_users = []
    for month in monthly_impact['year_month_str']:
        # Get all users whose first stuck order was in or before this month
        users_up_to_month = user_first_impact[user_first_impact['year_month'].astype(str) <= month]
        monthly_total_users.append(len(users_up_to_month))

    monthly_impact['total_users_up_to_month'] = monthly_total_users

    col1, col2 = st.columns(2)

    with col1:
        # Stacked area chart showing composition
        fig_composition = go.Figure()

        fig_composition.add_trace(go.Scatter(
            x=monthly_impact['year_month_str'],
            y=monthly_impact['new_users_impacted'],
            mode='lines',
            name='New Users This Month',
            stackgroup='one',
            fillcolor='rgba(255, 107, 107, 0.6)',
            line=dict(color='#FF6B6B', width=2)
        ))

        # Calculate existing users (cumulative - new)
        monthly_impact['existing_users'] = monthly_impact['cumulative_users'] - monthly_impact['new_users_impacted']
        fig_composition.add_trace(go.Scatter(
            x=monthly_impact['year_month_str'],
            y=monthly_impact['existing_users'],
            mode='lines',
            name='Previously Impacted Users',
            stackgroup='one',
            fillcolor='rgba(78, 205, 196, 0.4)',
            line=dict(color='#4ECDC4', width=2)
        ))

        fig_composition.update_layout(
            title='Monthly User Composition: New vs Previously Impacted',
            xaxis_title='Month',
            yaxis_title='Number of Users',
            hovermode='x unified',
            legend=dict(x=0.01, y=0.99)
        )
        st.plotly_chart(fig_composition, use_container_width=True)

    with col2:
        # Percentage composition
        monthly_impact['new_user_percentage'] = (
            monthly_impact['new_users_impacted'] / monthly_impact['cumulative_users'] * 100
        ).round(2)

        fig_percentage = px.bar(
            monthly_impact,
            x='year_month_str',
            y='new_user_percentage',
            title='New Users as % of Total Cumulative Users',
            labels={'year_month_str': 'Month', 'new_user_percentage': 'New Users (%)'},
            color='new_user_percentage',
            color_continuous_scale='Blues'
        )
        fig_percentage.add_hline(y=50, line_dash="dash", line_color="red",
                                 annotation_text="50% threshold")
        st.plotly_chart(fig_percentage, use_container_width=True)

    # Monthly breakdown table
    st.subheader("📊 Monthly Breakdown Table")

    # Calculate repeat users (users with multiple stuck orders in same month)
    monthly_impact_display = monthly_impact.copy()
    monthly_impact_display['repeat_orders'] = monthly_impact_display['total_stuck_orders'] - monthly_impact_display['new_users_impacted']
    monthly_impact_display['avg_orders_per_user'] = (monthly_impact_display['total_stuck_orders'] /
                                                       monthly_impact_display['new_users_impacted']).round(2)

    # Format for display
    display_cols = {
        'year_month_str': 'Month',
        'new_users_impacted': 'New Users Impacted',
        'cumulative_users': 'Cumulative Users',
        'total_stuck_orders': 'Total Stuck Orders',
        'repeat_orders': 'Orders from Existing Users',
        'avg_orders_per_user': 'Avg Orders/User'
    }

    monthly_table = monthly_impact_display[list(display_cols.keys())].copy()
    monthly_table.columns = list(display_cols.values())

    # Highlight recent months
    st.dataframe(
        monthly_table.style.background_gradient(subset=['New Users Impacted'], cmap='Reds'),
        use_container_width=True,
        height=400
    )

    # Download monthly data
    st.download_button(
        label="📥 Download Monthly Impact Data",
        data=monthly_table.to_csv(index=False),
        file_name=f"monthly_user_impact_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

    # Growth analysis
    st.subheader("📉 Growth Rate Analysis")

    col1, col2 = st.columns(2)

    with col1:
        # Calculate month-over-month growth
        monthly_impact_display['mom_growth'] = monthly_impact_display['new_users_impacted'].pct_change() * 100

        fig_growth = px.line(
            monthly_impact_display,
            x='year_month_str',
            y='mom_growth',
            title='Month-over-Month Growth Rate (%)',
            labels={'year_month_str': 'Month', 'mom_growth': 'Growth Rate (%)'},
            markers=True
        )
        fig_growth.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_growth, use_container_width=True)

    with col2:
        # Show acceleration/deceleration periods
        accelerating = monthly_impact_display[monthly_impact_display['mom_growth'] > 0]
        decelerating = monthly_impact_display[monthly_impact_display['mom_growth'] <= 0]

        st.metric("Months Accelerating", len(accelerating))
        st.metric("Months Decelerating", len(decelerating))

        if len(monthly_impact_display) >= 6:
            recent_6m = monthly_impact_display.tail(6)['new_users_impacted'].mean()
            older_6m = monthly_impact_display.head(max(1, len(monthly_impact_display)-6))['new_users_impacted'].mean()
            trend = ((recent_6m - older_6m) / older_6m * 100) if older_6m > 0 else 0
            st.metric("Trend (Last 6M vs Earlier)", f"{trend:+.1f}%")

    # Top affected users
    st.header("👥 Top Affected Users")

    user_counts = filtered_df['account_id'].value_counts().head(20).reset_index()
    user_counts.columns = ['User ID', 'Stuck Orders Count']

    col1, col2 = st.columns([2, 1])

    with col1:
        fig_users = px.bar(
            user_counts,
            x='User ID',
            y='Stuck Orders Count',
            title='Top 20 Users with Most Stuck Orders',
            color='Stuck Orders Count',
            color_continuous_scale='Oranges'
        )
        fig_users.update_xaxes(type='category')
        st.plotly_chart(fig_users, use_container_width=True)

    with col2:
        st.dataframe(user_counts, use_container_width=True, height=400)

    # Detailed statistics by vertical
    st.header("📊 Detailed Statistics by Vertical")

    stats_df = filtered_df.groupby('order_type_name').agg({
        'order_id': 'count',
        'account_id': 'nunique',
        'days_stuck': ['mean', 'median', 'min', 'max']
    }).round(2)

    stats_df.columns = ['Total Orders', 'Unique Users', 'Avg Days Stuck', 'Median Days Stuck', 'Min Days Stuck', 'Max Days Stuck']
    stats_df = stats_df.reset_index()
    stats_df.columns = ['Vertical', 'Total Orders', 'Unique Users', 'Avg Days Stuck', 'Median Days Stuck', 'Min Days Stuck', 'Max Days Stuck']

    st.dataframe(stats_df, use_container_width=True)

    # Order status distribution (if available)
    if 'order_status_name' in df.columns:
        st.header("📋 Order Status Distribution")
        status_vertical = filtered_df.groupby(['order_type_name', 'order_status_name']).size().reset_index(name='count')

        fig_status = px.bar(
            status_vertical,
            x='order_type_name',
            y='count',
            color='order_status_name',
            title='Order Status by Vertical',
            labels={'order_type_name': 'Vertical', 'count': 'Number of Orders'},
            barmode='group'
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # Data table
    st.header("📄 Detailed Data")

    # Display options
    col1, col2 = st.columns([3, 1])
    with col1:
        search_order = st.text_input("🔍 Search by Order ID")
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            options=['days_stuck', 'order_created_timestamp', 'travel_end_ts'],
            index=0
        )

    display_df = filtered_df.copy()

    if search_order:
        display_df = display_df[display_df['order_id'].astype(str).str.contains(search_order)]

    display_df = display_df.sort_values(by=sort_by, ascending=False)

    # Format for display
    display_df_formatted = display_df.copy()
    for col in timestamp_cols:
        if col in display_df_formatted.columns:
            display_df_formatted[col] = display_df_formatted[col].dt.strftime('%Y-%m-%d %H:%M:%S UTC')

    st.dataframe(
        display_df_formatted,
        use_container_width=True,
        height=400
    )

    # Download filtered data
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=display_df.to_csv(index=False),
        file_name=f"stuck_orders_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

    # Correlation & Causation Analysis
    if 'account_last_order_created_timestamp' in filtered_df.columns:
        st.header("🔗 Correlation & Causation Analysis: Stuck Orders vs Transaction Behavior")
        st.markdown("""
        This section analyzes whether experiencing stuck orders correlates with users stopping transactions.
        **Note**: Kafka finish publishing delays can take up to 7 days for high-volume periods, which may affect interpretation.
        """)

        # Define churn threshold (users who haven't ordered in X days)
        churn_threshold = st.slider("Days since last order to consider 'Churned'", 7, 90, 30, 7)

        # Classify users
        user_analysis = filtered_df.groupby('account_id').agg({
            'order_id': 'count',  # Total stuck orders per user
            'account_first_order_created_timestamp': 'first',
            'account_last_order_created_timestamp': 'first',
            'account_total_orders_during_analysis_period': 'first',
            'travel_end_ts': 'min',  # When they FIRST experienced stuck order
            'days_since_last_order': 'first',
            'order_type_name': lambda x: ', '.join(x.unique())  # Affected verticals
        }).reset_index()

        user_analysis.columns = ['account_id', 'stuck_orders_count', 'first_order_ts', 'last_order_ts',
                                 'total_orders', 'first_stuck_experience_ts', 'days_since_last_order',
                                 'affected_verticals']

        # Calculate days between first stuck order experience and last transaction
        user_analysis['days_first_stuck_to_last_order'] = (
            user_analysis['last_order_ts'] - user_analysis['first_stuck_experience_ts']
        ).dt.days

        # Classify user status
        user_analysis['user_status'] = user_analysis['days_since_last_order'].apply(
            lambda x: 'Churned' if x >= churn_threshold else 'Active'
        )

        # Classify if stuck order happened before or after last transaction
        user_analysis['stuck_timing'] = user_analysis['days_first_stuck_to_last_order'].apply(
            lambda x: 'After Last Order' if x < 0 else 'Before/During Active Period'
        )

        # Overview Metrics
        st.subheader("📊 User Behavior Overview")
        col1, col2, col3, col4 = st.columns(4)

        total_users = len(user_analysis)
        churned_users = len(user_analysis[user_analysis['user_status'] == 'Churned'])
        active_users = total_users - churned_users

        with col1:
            st.metric("Total Affected Users", f"{total_users:,}")
        with col2:
            st.metric("Churned Users", f"{churned_users:,}")
            st.caption(f"≥{churn_threshold} days inactive")
        with col3:
            st.metric("Active Users", f"{active_users:,}")
            st.caption(f"<{churn_threshold} days inactive")
        with col4:
            churn_rate = (churned_users / total_users * 100) if total_users > 0 else 0
            st.metric("Churn Rate", f"{churn_rate:.1f}%")

        # Stuck order timing analysis
        st.subheader("⏱️ When Did Stuck Orders Occur?")
        timing_counts = user_analysis['stuck_timing'].value_counts()

        col1, col2 = st.columns(2)
        with col1:
            fig_timing = px.pie(
                values=timing_counts.values,
                names=timing_counts.index,
                title='Stuck Order Timing Relative to Last Transaction',
                color_discrete_sequence=['#FF6B6B', '#4ECDC4']
            )
            st.plotly_chart(fig_timing, use_container_width=True)

        with col2:
            st.markdown("#### Interpretation:")
            after_last = timing_counts.get('After Last Order', 0)
            before_during = timing_counts.get('Before/During Active Period', 0)

            st.metric("Stuck AFTER last order", f"{after_last:,}")
            st.caption("User already stopped transacting when order got stuck")

            st.metric("Stuck BEFORE/DURING activity", f"{before_during:,}")
            st.caption("User was still active when stuck order occurred")

        # Churn analysis by stuck order experience
        st.subheader("📉 Churn Analysis by Stuck Order Count")

        # Categorize users by number of stuck orders
        user_analysis['stuck_order_category'] = pd.cut(
            user_analysis['stuck_orders_count'],
            bins=[0, 1, 2, 5, float('inf')],
            labels=['1 stuck order', '2 stuck orders', '3-5 stuck orders', '5+ stuck orders'],
            right=True
        )

        churn_by_stuck_count = user_analysis.groupby('stuck_order_category').agg({
            'account_id': 'count',
            'user_status': lambda x: (x == 'Churned').sum()
        }).reset_index()
        churn_by_stuck_count.columns = ['Stuck Order Category', 'Total Users', 'Churned Users']
        churn_by_stuck_count['Churn Rate (%)'] = (
            churn_by_stuck_count['Churned Users'] / churn_by_stuck_count['Total Users'] * 100
        ).round(2)

        col1, col2 = st.columns(2)

        with col1:
            fig_churn_rate = px.bar(
                churn_by_stuck_count,
                x='Stuck Order Category',
                y='Churn Rate (%)',
                title='Churn Rate by Number of Stuck Orders',
                color='Churn Rate (%)',
                color_continuous_scale='Reds',
                text='Churn Rate (%)'
            )
            fig_churn_rate.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_churn_rate, use_container_width=True)

        with col2:
            st.dataframe(
                churn_by_stuck_count.style.background_gradient(subset=['Churn Rate (%)'], cmap='Reds'),
                use_container_width=True,
                height=250
            )

        # Time-to-churn analysis (for users who stuck BEFORE/DURING activity)
        st.subheader("⏳ Time-to-Churn After Stuck Order Experience")

        before_during_users = user_analysis[user_analysis['stuck_timing'] == 'Before/During Active Period'].copy()

        if len(before_during_users) > 0:
            # For users who experienced stuck order while active
            before_during_users['time_to_churn_days'] = before_during_users['days_first_stuck_to_last_order']

            col1, col2 = st.columns(2)

            with col1:
                # Distribution of time to churn
                fig_time_to_churn = px.histogram(
                    before_during_users,
                    x='time_to_churn_days',
                    nbins=50,
                    title='Days from First Stuck Order to Last Transaction',
                    labels={'time_to_churn_days': 'Days to Last Order', 'count': 'Number of Users'},
                    color_discrete_sequence=['#FF6B6B']
                )
                st.plotly_chart(fig_time_to_churn, use_container_width=True)

            with col2:
                st.markdown("#### Key Statistics:")
                median_time = before_during_users['time_to_churn_days'].median()
                mean_time = before_during_users['time_to_churn_days'].mean()
                immediate_churn = len(before_during_users[before_during_users['time_to_churn_days'] <= 7])

                st.metric("Median Days to Last Order", f"{median_time:.0f}")
                st.metric("Mean Days to Last Order", f"{mean_time:.0f}")
                st.metric("Stopped within 7 days", f"{immediate_churn:,}")
                st.caption(f"{(immediate_churn/len(before_during_users)*100):.1f}% of users")

        # Churn by vertical
        st.subheader("🎯 Churn Rate by Affected Vertical")

        # Create vertical-level analysis
        vertical_churn = []
        for vertical in filtered_df['order_type_name'].unique():
            vertical_users = user_analysis[user_analysis['affected_verticals'].str.contains(vertical)]
            total = len(vertical_users)
            churned = len(vertical_users[vertical_users['user_status'] == 'Churned'])
            churn_rate = (churned / total * 100) if total > 0 else 0

            vertical_churn.append({
                'Vertical': vertical,
                'Total Users': total,
                'Churned Users': churned,
                'Active Users': total - churned,
                'Churn Rate (%)': round(churn_rate, 2)
            })

        vertical_churn_df = pd.DataFrame(vertical_churn).sort_values('Churn Rate (%)', ascending=False)

        col1, col2 = st.columns([2, 1])

        with col1:
            fig_vertical_churn = px.bar(
                vertical_churn_df,
                x='Vertical',
                y='Churn Rate (%)',
                title='Churn Rate by Vertical',
                color='Churn Rate (%)',
                color_continuous_scale='Reds',
                text='Churn Rate (%)'
            )
            fig_vertical_churn.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(fig_vertical_churn, use_container_width=True)

        with col2:
            st.dataframe(
                vertical_churn_df.style.background_gradient(subset=['Churn Rate (%)'], cmap='Reds'),
                use_container_width=True,
                height=400
            )

        # User segments comparison
        st.subheader("👥 User Segment Comparison: Churned vs Active")

        comparison_data = user_analysis.groupby('user_status').agg({
            'stuck_orders_count': ['mean', 'median'],
            'total_orders': ['mean', 'median'],
            'days_since_last_order': 'mean'
        }).round(2)

        comparison_data.columns = ['Avg Stuck Orders', 'Median Stuck Orders',
                                   'Avg Total Orders', 'Median Total Orders',
                                   'Avg Days Since Last Order']
        comparison_data = comparison_data.reset_index()

        st.dataframe(comparison_data, use_container_width=True)

        # Statistical insights
        st.subheader("📈 Statistical Correlation")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("#### Correlation Strength")
            # Calculate correlation between stuck orders and churn
            user_analysis['is_churned'] = (user_analysis['user_status'] == 'Churned').astype(int)
            correlation = user_analysis[['stuck_orders_count', 'is_churned']].corr().iloc[0, 1]

            st.metric("Stuck Orders ↔ Churn", f"{correlation:.3f}")
            if abs(correlation) < 0.3:
                st.caption("Weak correlation")
            elif abs(correlation) < 0.7:
                st.caption("Moderate correlation")
            else:
                st.caption("Strong correlation")

        with col2:
            st.markdown("#### Immediate Impact")
            immediate_impact = len(before_during_users[before_during_users['time_to_churn_days'] <= 7])
            total_before_during = len(before_during_users)
            immediate_rate = (immediate_impact / total_before_during * 100) if total_before_during > 0 else 0

            st.metric("Stopped ≤7 days after stuck", f"{immediate_rate:.1f}%")
            st.caption(f"{immediate_impact:,} of {total_before_during:,} users")

        with col3:
            st.markdown("#### Kafka Delay Factor")
            # Users who might still be in Kafka queue (stopped within 7 days)
            potential_kafka_delay = len(user_analysis[user_analysis['days_since_last_order'] <= 7])
            st.metric("Potentially in Kafka Queue", f"{potential_kafka_delay:,}")
            st.caption("Last order ≤7 days ago")

        # Interpretation guide
        st.info("""
        **📝 Interpretation Guide:**

        - **"After Last Order"**: The stuck order occurred AFTER the user's last transaction. This suggests the stuck order did NOT cause the user to stop transacting.

        - **"Before/During Active Period"**: The stuck order occurred while the user was still active. Analyzing time-to-churn helps determine causation.

        - **Kafka Delay Consideration**: Orders may take up to 7 days to finish during high-volume periods. Users inactive for <7 days might still be active.

        - **Correlation ≠ Causation**: High churn rates don't necessarily mean stuck orders caused churn. Other factors (seasonal behavior, satisfaction, competition) may be involved.
        """)

        # Download correlation analysis data
        st.download_button(
            label="📥 Download User Correlation Analysis",
            data=user_analysis.to_csv(index=False),
            file_name=f"user_correlation_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    # Key insights
    st.header("💡 Key Insights")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Most Affected Vertical")
        top_vertical = filtered_df['order_type_name'].value_counts().iloc[0]
        top_vertical_name = filtered_df['order_type_name'].value_counts().index[0]
        st.metric(top_vertical_name, f"{top_vertical:,} orders")
        st.metric("Percentage", f"{(top_vertical/len(filtered_df)*100):.1f}%")

    with col2:
        st.subheader("Longest Stuck Order")
        longest_idx = filtered_df['days_stuck'].idxmax()
        longest_order = filtered_df.loc[longest_idx]
        st.metric("Order ID", longest_order['order_id'])
        st.metric("Days Stuck", f"{longest_order['days_stuck']:.0f}")
        st.metric("Vertical", longest_order['order_type_name'])

    with col3:
        st.subheader("Orders > 30 Days Stuck")
        old_orders = filtered_df[filtered_df['days_stuck'] > 30]
        st.metric("Count", f"{len(old_orders):,}")
        st.metric("Percentage", f"{(len(old_orders)/len(filtered_df)*100):.1f}%")

else:
    st.info("👆 Please upload a CSV file to begin analysis")

    st.markdown("""
    ### Expected CSV Format:
    - `order_created_timestamp`: When the order was created
    - `order_id`: Unique order identifier
    - `account_id`: User/account identifier
    - `order_type_name`: Vertical (event, hotel, flight, etc.)
    - `order_status_name`: Current order status
    - `travel_start_ts`: When the travel/event starts
    - `travel_end_ts`: When the travel/event ends
    """)

    st.markdown("""
    ### About This Analysis:
    This tool helps identify and analyze orders that should have transitioned to `finished` status but remain stuck
    in `eticket_issued` status even after their travel end date has passed. The dashboard provides:

    - Overall metrics and trends
    - Breakdown by vertical (event, hotel, flight, etc.)
    - Time-based analysis
    - User impact analysis
    - Detailed order data with search and filter capabilities
    """)
