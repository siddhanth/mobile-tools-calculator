"""
PMS Analysis Tab
Analyze PMS holdings from multiple providers
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import sys
import tempfile
import os

# Add pms module to path
pms_path = Path(__file__).parent.parent / "pms"
sys.path.insert(0, str(pms_path))

from database.db_manager import DatabaseManager
from parsers import PARSER_REGISTRY, get_parser


def get_db():
    """Get database connection."""
    db_path = Path(__file__).parent.parent / "pms" / "pms_data.db"
    return DatabaseManager(str(db_path))


def format_currency(value):
    """Format value as Indian currency."""
    if value is None:
        return "-"
    if value >= 10000000:  # 1 crore
        return f"₹{value/10000000:.2f} Cr"
    elif value >= 100000:  # 1 lakh
        return f"₹{value/100000:.2f} L"
    else:
        return f"₹{value:,.0f}"


def render_sidebar():
    """Render sidebar filters for PMS."""
    st.sidebar.markdown("### 🏢 PMS Filters")
    
    with get_db() as db:
        reports = db.get_reports()
    
    if not reports:
        st.sidebar.info("No PMS reports uploaded yet")
        return None, None
    
    # Provider filter
    providers = list(set(r['pms_provider'] for r in reports))
    providers.insert(0, "All Providers")
    
    selected_provider = st.sidebar.selectbox(
        "Provider",
        providers,
        key="pms_provider_filter"
    )
    
    # Report selector
    if selected_provider != "All Providers":
        filtered_reports = [r for r in reports if r['pms_provider'] == selected_provider]
    else:
        filtered_reports = reports
    
    report_options = {
        f"{r['pms_provider'].title()} - {r['report_date']}": r['id'] 
        for r in filtered_reports
    }
    report_options["All Reports"] = None
    
    selected_report_label = st.sidebar.selectbox(
        "Report",
        list(report_options.keys()),
        key="pms_report_filter"
    )
    selected_report_id = report_options[selected_report_label]
    
    return selected_provider, selected_report_id


def render_upload_section():
    """Render the upload section in sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📤 Upload Report")
    
    with st.sidebar.expander("Upload New PMS Report", expanded=False):
        provider = st.selectbox(
            "Select Provider",
            list(PARSER_REGISTRY.keys()),
            format_func=lambda x: x.title(),
            key="upload_provider"
        )
        
        uploaded_file = st.file_uploader(
            "Upload PDF",
            type=['pdf'],
            help="Upload a PMS holding report PDF",
            key="pms_uploader"
        )
        
        if uploaded_file and st.button("🚀 Process Report", key="process_btn"):
            process_uploaded_file(uploaded_file, provider)


def process_uploaded_file(uploaded_file, provider):
    """Process an uploaded PDF file."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name
    
    try:
        parser_class = get_parser(provider)
        parser = parser_class(tmp_path)
        
        with st.spinner('Parsing PDF...'):
            result = parser.parse()
        
        with get_db() as db:
            file_hash = db.compute_file_hash(tmp_path)
            
            if db.report_exists(provider, result['report_date'], file_hash):
                st.warning("⚠️ This report already exists in the database.")
                return
            
            report_id = db.insert_report(
                pms_provider=provider,
                report_date=result['report_date'],
                file_path=uploaded_file.name,
                file_hash=file_hash
            )
            
            db.insert_holdings(report_id, result['holdings'])
        
        st.success(f"✅ Imported {len(result['holdings'])} holdings from {result['report_date']}!")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
    finally:
        os.unlink(tmp_path)


def render_overview(provider_filter, report_id):
    """Render the overview section."""
    st.markdown("## 📈 Portfolio Overview")
    
    with get_db() as db:
        if report_id:
            reports = [db.get_report_by_id(report_id)]
            holdings = db.get_holdings(report_id=report_id)
        else:
            reports = db.get_reports(
                pms_provider=provider_filter if provider_filter != "All Providers" else None
            )
            holdings = []
            for r in reports:
                holdings.extend(db.get_holdings(report_id=r['id']))
    
    if not holdings:
        st.info("📭 No holdings data available. Upload a PMS report to get started.")
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(holdings)
    
    # Calculate metrics
    total_value = df['market_value'].sum() if 'market_value' in df else 0
    total_stocks = len(df[df['market_value'].notna()])
    avg_return = df['gain_loss_percentage'].mean() if 'gain_loss_percentage' in df else 0
    total_gain = df['gain_loss'].sum() if 'gain_loss' in df else 0
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Total Value",
            format_currency(total_value),
            help="Total market value of all holdings"
        )
    
    with col2:
        st.metric(
            "📊 Holdings",
            f"{total_stocks}",
            help="Number of holdings"
        )
    
    with col3:
        st.metric(
            "📈 Avg Return",
            f"{avg_return:.2f}%" if avg_return else "-",
            delta=f"{avg_return:.2f}%" if avg_return else None,
            help="Average return across holdings"
        )
    
    with col4:
        st.metric(
            "💹 Total Gain/Loss",
            format_currency(total_gain) if total_gain else "-",
            delta=format_currency(total_gain) if total_gain else None,
            help="Total unrealized gain/loss"
        )
    
    return df


def render_holdings_table(df):
    """Render the holdings table."""
    st.markdown("## 📋 Holdings Details")
    
    if df is None or df.empty:
        return
    
    # Prepare display DataFrame
    display_cols = [
        'stock_name', 'sector', 'quantity', 'cost_price', 'current_price',
        'market_value', 'portfolio_percentage', 'gain_loss_percentage'
    ]
    
    display_df = df[[c for c in display_cols if c in df.columns]].copy()
    
    # Rename columns for display
    column_names = {
        'stock_name': 'Stock',
        'sector': 'Category',
        'quantity': 'Qty',
        'cost_price': 'Avg Cost',
        'current_price': 'CMP',
        'market_value': 'Value',
        'portfolio_percentage': 'Weight %',
        'gain_loss_percentage': 'Return %'
    }
    display_df = display_df.rename(columns=column_names)
    
    # Sort by value
    if 'Value' in display_df.columns:
        display_df = display_df.sort_values('Value', ascending=False)
    
    # Format numeric columns
    format_config = {}
    if 'Value' in display_df.columns:
        display_df['Value'] = display_df['Value'].apply(lambda x: f"₹{x:,.0f}" if pd.notna(x) else "-")
    if 'Avg Cost' in display_df.columns:
        display_df['Avg Cost'] = display_df['Avg Cost'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "-")
    if 'CMP' in display_df.columns:
        display_df['CMP'] = display_df['CMP'].apply(lambda x: f"₹{x:,.2f}" if pd.notna(x) else "-")
    if 'Qty' in display_df.columns:
        display_df['Qty'] = display_df['Qty'].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")
    if 'Weight %' in display_df.columns:
        display_df['Weight %'] = display_df['Weight %'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
    if 'Return %' in display_df.columns:
        display_df['Return %'] = display_df['Return %'].apply(lambda x: f"{x:+.2f}%" if pd.notna(x) else "-")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )


def render_charts(df):
    """Render portfolio charts."""
    if df is None or df.empty:
        return
    
    st.markdown("## 📊 Portfolio Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Allocation pie chart
        if 'portfolio_percentage' in df.columns and df['portfolio_percentage'].notna().any():
            fig = px.pie(
                df[df['portfolio_percentage'].notna()],
                values='portfolio_percentage',
                names='stock_name',
                title='Portfolio Allocation',
                color_discrete_sequence=px.colors.sequential.Blues
            )
            fig.update_layout(
                paper_bgcolor='white',
                plot_bgcolor='white',
                font_color='#2c3e50',
                title_font_color='#1a73e8',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top holdings bar chart
        if 'market_value' in df.columns and df['market_value'].notna().any():
            plot_df = df[df['market_value'].notna()].nlargest(10, 'market_value')
            
            fig = px.bar(
                plot_df,
                x='stock_name',
                y='market_value',
                title='Top 10 Holdings by Value',
                color='market_value',
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                paper_bgcolor='white',
                plot_bgcolor='white',
                font_color='#2c3e50',
                title_font_color='#1a73e8',
                xaxis_title='',
                yaxis_title='Value (₹)',
                showlegend=False,
                xaxis_tickangle=-45,
                height=400,
                xaxis=dict(gridcolor='#e1e4e8'),
                yaxis=dict(gridcolor='#e1e4e8')
            )
            fig.update_coloraxes(showscale=False)
            st.plotly_chart(fig, use_container_width=True)
    
    # Returns chart
    if 'gain_loss_percentage' in df.columns and df['gain_loss_percentage'].notna().any():
        st.markdown("### 📈 Returns by Holding")
        
        returns_df = df[df['gain_loss_percentage'].notna()].copy()
        returns_df = returns_df.sort_values('gain_loss_percentage', ascending=True)
        
        colors = ['#f44336' if x < 0 else '#4caf50' for x in returns_df['gain_loss_percentage']]
        
        fig = go.Figure(go.Bar(
            x=returns_df['gain_loss_percentage'],
            y=returns_df['stock_name'],
            orientation='h',
            marker_color=colors,
            text=[f"{x:+.1f}%" for x in returns_df['gain_loss_percentage']],
            textposition='outside'
        ))
        
        fig.update_layout(
            paper_bgcolor='white',
            plot_bgcolor='white',
            font_color='#2c3e50',
            title='Returns by Holding',
            title_font_color='#1a73e8',
            xaxis_title='Return %',
            yaxis_title='',
            height=max(300, len(returns_df) * 40),
            xaxis=dict(zeroline=True, zerolinecolor='#bdbdbd', gridcolor='#e1e4e8'),
            yaxis=dict(gridcolor='#e1e4e8')
        )
        
        st.plotly_chart(fig, use_container_width=True)


def render_reports_table():
    """Render reports management table."""
    st.markdown("## 📁 Reports Management")
    
    with get_db() as db:
        reports = db.get_reports()
    
    if not reports:
        st.info("No reports in database.")
        return
    
    reports_df = pd.DataFrame(reports)
    reports_df['uploaded_at'] = pd.to_datetime(reports_df['uploaded_at']).dt.strftime('%Y-%m-%d %H:%M')
    
    display_df = reports_df[['id', 'pms_provider', 'report_date', 'file_path', 'uploaded_at']].copy()
    display_df.columns = ['ID', 'Provider', 'Report Date', 'File', 'Imported At']
    display_df['Provider'] = display_df['Provider'].str.title()
    display_df['File'] = display_df['File'].apply(lambda x: Path(x).name if x else '-')
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Delete functionality
    with st.expander("🗑️ Delete Report"):
        if reports:
            report_to_delete = st.selectbox(
                "Select report to delete",
                [f"ID {r['id']}: {r['pms_provider']} - {r['report_date']}" for r in reports],
                key="delete_report_select"
            )
            
            if st.button("Delete Selected Report", type="secondary", key="delete_btn"):
                report_id = int(report_to_delete.split(':')[0].replace('ID ', ''))
                with get_db() as db:
                    db.delete_report(report_id)
                st.success("Report deleted!")
                st.rerun()


def render():
    """Main render function for PMS tab."""
    st.title("🏢 PMS Portfolio Analysis")
    st.markdown("*Track and analyze your Portfolio Management Service holdings*")
    st.markdown("---")
    
    # Sidebar filters
    provider_filter, report_id = render_sidebar()
    render_upload_section()
    
    # Check if there's any data
    with get_db() as db:
        reports = db.get_reports()
    
    if not reports:
        st.info("👋 Welcome to PMS Analyzer! Upload your first PMS report to get started.")
        st.markdown("""
        ### How to use:
        1. **Upload a Report**: Use the sidebar to upload a PMS holding report PDF
        2. **Select Provider**: Choose your PMS provider (currently supports Sameeksha)
        3. **View Analysis**: Explore your portfolio metrics, holdings, and returns
        4. **Compare Reports**: Upload multiple reports to track changes over time
        """)
        return
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📈 Overview", "📊 Analysis", "📁 Reports"])
    
    with tab1:
        df = render_overview(provider_filter, report_id)
        if df is not None:
            render_holdings_table(df)
    
    with tab2:
        with get_db() as db:
            if report_id:
                holdings = db.get_holdings(report_id=report_id)
            else:
                reports_list = db.get_reports(
                    pms_provider=provider_filter if provider_filter != "All Providers" else None
                )
                holdings = []
                for r in reports_list:
                    holdings.extend(db.get_holdings(report_id=r['id']))
        
        if holdings:
            df = pd.DataFrame(holdings)
            render_charts(df)
        else:
            st.info("📭 No data available for analysis.")
    
    with tab3:
        render_reports_table()

