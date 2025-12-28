## Daily Cost Report - {{ date }}
**Total Daily Cost: ${{ "%.2f"|format(total_daily) }}/day** (${{ "%.2f"|format(total_monthly) }}/month)
**MTD ({{ days_elapsed }} days): ${{ "%.2f"|format(total_mtd) }}**
{% if droplets %}
### Droplets (MTD: ${{ "%.2f"|format(droplets_mtd) }})
{% for r in droplets -%}
• **{{ r.name }}**: ${{ "%.2f"|format(r.cost) }}/day | MTD: ${{ "%.2f"|format(r.mtd) }} - {{ r.specs }}
{% endfor -%}
{% endif -%}
{% if volumes %}
### Volumes (MTD: ${{ "%.2f"|format(volumes_mtd) }})
{% for r in volumes -%}
• **{{ r.name }}**: ${{ "%.4f"|format(r.cost) }}/day | MTD: ${{ "%.2f"|format(r.mtd) }} - {{ r.size_gb }}GB ({{ r.count }} {% if r.count == 1 %}volume{% else %}volumes{% endif %})
{% endfor -%}
{% endif -%}
{% if lb_count > 0 %}
### Load Balancers (MTD: ${{ "%.2f"|format(lb_mtd) }})
• **{{ lb_count }} LB**: ${{ "%.2f"|format(lb_cost) }}/day | MTD: ${{ "%.2f"|format(lb_mtd) }}
{% endif %}
