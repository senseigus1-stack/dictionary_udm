{{- define "zechbur.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "zechbur.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "zechbur.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "zechbur.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "zechbur.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "zechbur.selectorLabels" -}}
app.kubernetes.io/name: {{ include "zechbur.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "zechbur.secretName" -}}
{{- default (printf "%s-secrets" (include "zechbur.fullname" .)) .Values.secrets.existingSecret }}
{{- end }}

{{- define "zechbur.databaseHost" -}}
{{- printf "%s-postgres" (include "zechbur.fullname" .) }}
{{- end }}

{{- define "zechbur.redisHost" -}}
{{- printf "%s-redis" (include "zechbur.fullname" .) }}
{{- end }}
