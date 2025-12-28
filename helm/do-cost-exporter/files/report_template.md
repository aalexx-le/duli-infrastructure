## Daily Cost Report - {{ date }}
**Total Daily Cost: ${{ "%.2f"|format(total_daily) }}/day** (${{ "%.2f"|format(total_monthly) }}/month)
{% if mtd %}
**MTD ({{ mtd.billing_period }}): ${{ "%.2f"|format(mtd.total) }}**
{% endif %}
{% if droplets %}
### Droplets{% if mtd %} (MTD: ${{ "%.2f"|format(mtd.droplets) }}){% endif %}
{% for r in droplets -%}
• **{{ r.name }}**: ${{ "%.2f"|format(r.cost) }}/day - {{ r.specs }}
{% endfor -%}
{% endif -%}
{% if volumes %}
### Volumes{% if mtd %} (MTD: ${{ "%.2f"|format(mtd.volumes) }}){% endif %}
{% for r in volumes -%}
• **{{ r.name }}**: ${{ "%.4f"|format(r.cost) }}/day - {{ r.size_gb }}GB ({{ r.count }} {% if r.count == 1 %}volume{% else %}volumes{% endif %})
{% endfor -%}
{% endif -%}
{% if lb_count > 0 %}
### Load Balancers{% if mtd %} (MTD: ${{ "%.2f"|format(mtd.load_balancers) }}){% endif %}
• **{{ lb_count }} LB**: ${{ "%.2f"|format(lb_cost) }}/day
{% endif %}
