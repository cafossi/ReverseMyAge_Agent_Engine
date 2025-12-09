def export_pareto_html_report(
    start_date: str,
    end_date: str,
    mode: str,
    format: str = 'html',
    output_dir: str = './reports',
    customer_code: Optional[int] = None,
    customer_name: Optional[str] = None,  # ← ADD THIS
    region: Optional[str] = None,
    selected_locations: Optional[List[str]] = None,
    filename: Optional[str] = None
) -> str:
    """
    Generate and export NEW HTML-based Pareto report (with interactive features).
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)  (used as week_ending_date)
        mode: 'customer' or 'region'
        format: 'html' or 'pdf'
        output_dir: Directory to save report
        customer_code: Required for customer mode
        customer_name: Optional customer name (used for filename if provided)  # ← ADD THIS
        region: Required for region mode
        selected_locations: Optional list of location IDs
        filename: Optional custom filename (without extension)
    
    Returns:
        Path to generated file
    """
    from .schedule_reports.reports.pareto_optimization_html import generate_pareto_optimization_html
    from .common.filename_utils import generate_pareto_optimization_filename
    
    # Validate inputs
    if mode == 'customer' and not customer_code:
        raise ValueError("customer_code required for customer mode")
    if mode == 'region' and not region:
        raise ValueError("region required for region mode")
    
    # Generate HTML content
    html_content = generate_pareto_optimization_html(
        start_date=start_date,
        end_date=end_date,
        mode=mode,
        customer_code=customer_code,
        region=region,
        selected_locations=selected_locations
    )
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # ✅ UPDATED: Generate standardized filename
    if not filename:
        if mode == 'customer':
            # Use customer_name if provided, otherwise use customer_code
            identifier = customer_name if customer_name else str(customer_code)
            mode_label = 'Customer'
        else:
            identifier = region
            mode_label = 'Region'
        
        # Generate standardized filename (WITHOUT extension)
        filename = generate_pareto_optimization_filename(
            mode=mode_label,
            scope_identifier=identifier,
            week_ending_date=end_date,
            extension=''  # Don't add extension here, we'll add it below
        ).replace('.', '')  # Remove any dots
    
    # Export based on format
    if format.lower() == 'html':
        output_path = os.path.join(output_dir, f"{filename}.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML report saved: {output_path}")
        return output_path
    
    elif format.lower() == 'pdf':
        output_path = os.path.join(output_dir, f"{filename}.pdf")
        html_to_pdf(html_content, output_path)
        print(f"✅ PDF report saved: {output_path}")
        return output_path
    
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'html' or 'pdf'")