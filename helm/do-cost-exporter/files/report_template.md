# 💰 Daily Cost Report - {{ date }}

**Total Daily Cost: ${{ "%.2f"|format(total_daily) }}/day** (${{ "%.2f"|format(total_monthly) }}/month)

{% if droplets %}
## 🖥️ Droplets
{% for r in droplets %}
• **{{ r.name }}**: ${{ "%.2f"|format(r.cost) }}/day - {{ r.specs }}
{% endfor %}
{% endif %}
{% if volumes %}
## 💾 Volumes
{% for r in volumes %}
• **{{ r.name[:20] }}...**: ${{ "%.4f"|format(r.cost) }}/day - {{ r.specs }}
{% endfor %}
{% endif %}
{% if loadbalancers %}
## ⚖️ Load Balancers
{% for r in loadbalancers %}
• **{{ r.name[:20] }}...**: ${{ "%.2f"|format(r.cost) }}/day
{% endfor %}
{% endif %}
