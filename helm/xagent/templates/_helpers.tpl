{{/*
Expand the name of the chart.
*/}}
{{- define "xagent.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "xagent.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "xagent.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "xagent.labels" -}}
helm.sh/chart: {{ include "xagent.chart" . }}
{{ include "xagent.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "xagent.selectorLabels" -}}
app.kubernetes.io/name: {{ include "xagent.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API specific labels
*/}}
{{- define "xagent.api.labels" -}}
{{ include "xagent.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API selector labels
*/}}
{{- define "xagent.api.selectorLabels" -}}
{{ include "xagent.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
WebSocket specific labels
*/}}
{{- define "xagent.websocket.labels" -}}
{{ include "xagent.labels" . }}
app.kubernetes.io/component: websocket
{{- end }}

{{/*
WebSocket selector labels
*/}}
{{- define "xagent.websocket.selectorLabels" -}}
{{ include "xagent.selectorLabels" . }}
app.kubernetes.io/component: websocket
{{- end }}

{{/*
Worker specific labels
*/}}
{{- define "xagent.worker.labels" -}}
{{ include "xagent.labels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Worker selector labels
*/}}
{{- define "xagent.worker.selectorLabels" -}}
{{ include "xagent.selectorLabels" . }}
app.kubernetes.io/component: worker
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "xagent.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "xagent.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Redis URL
*/}}
{{- define "xagent.redisUrl" -}}
{{- if .Values.redis.enabled }}
{{- printf "redis://:%s@%s-redis-master:6379/0" .Values.redis.auth.password .Release.Name }}
{{- else }}
{{- .Values.externalRedis.url }}
{{- end }}
{{- end }}

{{/*
PostgreSQL URL
*/}}
{{- define "xagent.postgresUrl" -}}
{{- if .Values.postgresql.enabled }}
{{- printf "postgresql://%s:%s@%s-postgresql:5432/%s" .Values.postgresql.auth.username .Values.postgresql.auth.password .Release.Name .Values.postgresql.auth.database }}
{{- else }}
{{- .Values.externalPostgresql.url }}
{{- end }}
{{- end }}

{{/*
ChromaDB URL
*/}}
{{- define "xagent.chromaUrl" -}}
{{- if .Values.chromadb.enabled }}
{{- printf "http://%s-chromadb:%d" (include "xagent.fullname" .) (.Values.chromadb.service.port | int) }}
{{- else }}
{{- .Values.externalChroma.url }}
{{- end }}
{{- end }}
