## Cost Report ({{ period.start }} - {{ period.today }})
| Today | MTD | Est. Month |
|-------|-----|------------|
| ${{ "%.2f"|format(total_today) }} | ${{ "%.2f"|format(total_mtd) }} | ${{ "%.2f"|format(total_estimated) }} |
{% if droplets %}
### Droplets (${{ "%.2f"|format(droplets_mtd) }})
{% for r in droplets -%}
• **{{ r.name }}**: ${{ "%.2f"|format(r.mtd) }} - {{ r.specs }}
{% endfor -%}
{% endif -%}
{% if volumes %}
### Volumes (${{ "%.2f"|format(volumes_mtd) }})
{% for r in volumes -%}
• **{{ r.name }}**: ${{ "%.2f"|format(r.mtd) }} - {{ r.size_gb }}GB ({{ r.count }} {% if r.count == 1 %}volume{% else %}volumes{% endif %})
{% endfor -%}
{% endif -%}
{% if lb_count > 0 %}
### Load Balancers (${{ "%.2f"|format(lb_mtd) }})
• **{{ lb_count }} LB**: ${{ "%.2f"|format(lb_mtd) }}
{% endif %}
