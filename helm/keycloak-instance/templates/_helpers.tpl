{{- define "keycloak.httpOptions" -}}
- name: proxy-headers
  value: {{ .Values.keycloak.proxy.headers | quote }}
- name: proxy-mode
  value: {{ .Values.keycloak.proxy.mode | quote }}
{{- if not .Values.keycloak.tls.enabled }}
- name: http-enabled
  value: "true"
{{- end }}
{{- if .Values.keycloak.tls.enabled }}
- name: https-certificate-file
  value: "/etc/certs/tls.crt"
- name: https-certificate-key-file
  value: "/etc/certs/tls.key"
{{- end }}
{{- end }}
