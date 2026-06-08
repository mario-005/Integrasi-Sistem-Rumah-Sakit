# Hospital EAI System

Sistem Integrasi Rumah Sakit Berbasis Microservices menggunakan **RabbitMQ** dan **Docker**.

Proyek ini adalah implementasi **Enterprise Application Integration (EAI)** pattern untuk sistem rumah sakit yang terdiri dari beberapa service yang saling terintegrasi.

---

## Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────────┐
│                          NGINX API Gateway                          │
│                         (port 80)                                    │
└──┬──────────┬──────────┬──────────┬──────────┬──────────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌──────────────┐
│ Reg  │ │ Medical│ │Pharm │ │ Bill│ │ Integration   │
│ Svc  │ │ Rec Svc│ │ Svc  │ │ Svc  │ │ Service       │
│:8001 │ │ :8002  │ │:8003 │ │:8004 │ │ :8005         │
└──┬───┘ └──┬─────┘ └──┬───┘ └──┬───┘ └──────┬───────┘
   │        │          │        │             │
   ▼        ▼          ▼        ▼             ▼
┌──────┐ ┌────────┐ ┌──────┐ ┌──────┐ ┌────────────┐
│Post- │ │ MySQL  │ │Mongo │ │Post- │ │  RabbitMQ  │
│greSQL│ │        │ │ DB   │ │greSQL│ │  Message   │
│  :5432│ │ :3306  │ │:27017│ │ :5433│ │  Broker    │
└──────┘ └────────┘ └──────┘ └──────┘ └────────────┘
```

### Diagram Integrasi Event-Driven

```
Registration     Integration      Medical Record     Pharmacy       Billing
  Service         Service           Service          Service        Service
    │                │                  │               │              │
    │ ── Publish ──▶│                  │               │              │
    │ PatientReg.   │                  │               │              │
    │                │ ── JSON→XML ──▶ │               │              │
    │                │   (Translator)  │               │              │
    │                │                  │               │              │
    │                │                  │ ── Publish ──▶│              │
    │                │                  │ Presc.Created │              │
    │                │ ◀────────────────│               │              │
    │                │ ── XML→JSON ──▶ │               │              │
    │                │   (Translator)  │               │              │
    │                │                  │               │              │
    │                │                  │               │ ── Publish ─▶│
    │                │                  │               │ Med.Disp.    │
    │                │ ◀────────────────────────────────│              │
    │                │                  │               │              │
    │                │ ────────────────────────────────────────────▶ │
    │                │   (Forward to Billing)           │              │
    │                │                  │               │              │
    │                │                  │               │          ── Publish ─▶
    │                │                  │               │          Invoice.     │
    │                │ ◀──────────────────────────────────────────────│
    │                │   (Log Invoice)  │               │              │
```

---

## Daftar Service

| Service | Teknologi | Database | Port |
|---------|-----------|----------|------|
| **Registration Service** | Python FastAPI | PostgreSQL | 8001 |
| **Medical Record Service** | Python FastAPI | MySQL | 8002 |
| **Pharmacy Service** | Python FastAPI | MongoDB | 8003 |
| **Billing Service** | Python FastAPI | PostgreSQL | 8004 |
| **Integration Service** | Python FastAPI | - | 8005 |
| **Nginx API Gateway** | Nginx | - | 80 |
| **RabbitMQ** | RabbitMQ + Management | - | 5672, 15672 |

---

## Daftar Database

| Database | Service | DBMS | Tabel/Koleksi |
|----------|---------|------|---------------|
| `registration_db` | Registration Service | PostgreSQL | `patients` |
| `medical_db` | Medical Record Service | MySQL | `medical_records` |
| `pharmacy_db` | Pharmacy Service | MongoDB | `medicines`, `prescriptions` |
| `billing_db` | Billing Service | PostgreSQL | `invoices` |

---

## Daftar Queue RabbitMQ

| Queue | DLQ | Producer | Consumer |
|-------|-----|----------|----------|
| `patient_registered_queue` | `dlq_patient_registered_queue` | Registration Service | Integration Service |
| `prescription_created_queue` | `dlq_prescription_created_queue` | Medical Record Service | Integration Service |
| `medicine_dispensed_queue` | `dlq_medicine_dispensed_queue` | Pharmacy Service | Integration Service |
| `invoice_created_queue` | `dlq_invoice_created_queue` | Billing Service | Integration Service |

---

## Enterprise Integration Patterns

| No | Pattern | Implementasi |
|----|---------|--------------|
| 1 | **Message Channel** | RabbitMQ Queue sebagai saluran komunikasi |
| 2 | **Publish Subscribe** | Event Broadcasting melalui queue |
| 3 | **Message Endpoint** | Producer (setiap service) dan Consumer (Integration Service) |
| 4 | **Message Translator** | Transformasi JSON ↔ XML di Integration Service |
| 5 | **Content-Based Router** | Routing berdasarkan `event_type` di Integration Service |
| 6 | **Canonical Data Model** | Format standar event: `event_type`, `timestamp`, `tracing_id`, `payload` |

---

## Cara Menjalankan Sistem

### Prasyarat

- Docker & Docker Compose
- Git

### Langkah-langkah

```bash
# 1. Clone repository
git clone <repository-url>
cd hospital-eai

# 2. Jalankan semua service
docker compose up --build

# 3. Akses service
# Nginx Gateway: http://localhost
# Registration: http://localhost:8001/docs
# Medical Record: http://localhost:8002/docs
# Pharmacy: http://localhost:8003/docs
# Billing: http://localhost:8004/docs
# Integration: http://localhost:8005/docs
# RabbitMQ Management: http://localhost:15672 (guest/guest)
```

### Hentikan sistem

```bash
docker compose down -v
```

---

## Contoh API Request

### 1. Registrasi Pasien

```bash
curl -X POST http://localhost:8001/patients \
  -H "Content-Type: application/json" \
  -d '{
    "patient_code": "P001",
    "name": "Mario",
    "gender": "Male",
    "birth_date": "1990-01-15",
    "address": "Jl. Merdeka No. 1"
  }'
```

**Response:**
```json
{
  "id": 1,
  "patient_code": "P001",
  "name": "Mario",
  "gender": "Male",
  "birth_date": "1990-01-15",
  "address": "Jl. Merdeka No. 1",
  "created_at": "2026-06-09T03:00:00"
}
```

### 2. Cek Data Pasien

```bash
curl http://localhost:8001/patients
curl http://localhost:8001/patients/1
```

### 3. Tambah Rekam Medis (oleh Dokter)

```bash
curl -X POST http://localhost:8002/medical-records \
  -H "Content-Type: application/json" \
  -d '{
    "patient_code": "P001",
    "diagnosis": "Demam tinggi, suspect typoid",
    "doctor_name": "Dr. Andi",
    "prescription": "MED001:3,MED002:2"
  }'
```

### 4. Cek Stok Obat

```bash
curl http://localhost:8003/medicines
```

### 5. Cek Invoice

```bash
curl http://localhost:8004/invoices
```

### 6. Via Nginx Gateway

```bash
curl http://localhost/registration/patients
curl http://localhost/medical/medical-records
curl http://localhost/pharmacy/medicines
curl http://localhost/billing/invoices
```

---

## Contoh Event RabbitMQ

### PatientRegistered

```json
{
  "event_type": "PatientRegistered",
  "timestamp": "2026-06-09T03:00:00.000000",
  "tracing_id": "reg-1-1717894800",
  "payload": {
    "id": 1,
    "patient_code": "P001",
    "name": "Mario",
    "gender": "Male",
    "birth_date": "1990-01-15",
    "address": "Jl. Merdeka No. 1"
  }
}
```

### PrescriptionCreated

```json
{
  "event_type": "PrescriptionCreated",
  "timestamp": "2026-06-09T03:05:00.000000",
  "tracing_id": "med-1-1717895100",
  "payload": {
    "id": 1,
    "patient_code": "P001",
    "diagnosis": "Demam tinggi, suspect typoid",
    "doctor_name": "Dr. Andi",
    "prescription_xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<prescription>\n    <patient_code>P001</patient_code>\n    <diagnosis>Demam tinggi, suspect typoid</diagnosis>\n    <doctor_name>Dr. Andi</doctor_name>\n    <medication>MED001:3,MED002:2</medication>\n    <created_at>2026-06-09T03:05:00</created_at>\n</prescription>"
  }
}
```

### MedicineDispensed

```json
{
  "event_type": "MedicineDispensed",
  "timestamp": "2026-06-09T03:06:00.000000",
  "tracing_id": "pha-abc123-1717895160",
  "payload": {
    "id": "abc123",
    "patient_code": "P001",
    "medicine_code": "MED001",
    "medicine_name": "Paracetamol",
    "quantity": 3,
    "total_cost": 45000.0
  }
}
```

### InvoiceCreated

```json
{
  "event_type": "InvoiceCreated",
  "timestamp": "2026-06-09T03:07:00.000000",
  "tracing_id": "bil-1-1717895220",
  "payload": {
    "id": 1,
    "patient_code": "P001",
    "service_fee": 100000.0,
    "medicine_fee": 95000.0,
    "total_fee": 195000.0,
    "status": "pending"
  }
}
```

---

## Contoh Alur End-to-End

### Skenario Lengkap

```bash
# Step 1: Registrasi pasien
curl -X POST http://localhost:8001/patients \
  -H "Content-Type: application/json" \
  -d '{
    "patient_code": "P001",
    "name": "Mario",
    "gender": "Male",
    "birth_date": "1990-01-15",
    "address": "Jl. Merdeka No. 1"
  }'

# Step 2: Cek rekam medis (data dari Integration Service sudah masuk)
curl http://localhost:8002/medical-records

# Step 3: Dokumen menambah diagnosis dan resep
curl -X POST http://localhost:8002/medical-records \
  -H "Content-Type: application/json" \
  -d '{
    "patient_code": "P001",
    "diagnosis": "Demam tinggi, suspect typoid",
    "doctor_name": "Dr. Andi",
    "prescription": "MED001:3,MED002:2"
  }'

# Step 4: Cek stok obat berkurang
curl http://localhost:8003/medicines

# Step 5: Cek invoice yang terbuat otomatis
curl http://localhost:8004/invoices

# Step 6: Cek log Integration Service untuk trace lengkap
curl http://localhost:8005/integration/health
```

### Alur Sistem

1. **Registration Service** menyimpan pasien ke PostgreSQL dan publish `PatientRegistered`
2. **Integration Service** consume event, transform JSON → XML, kirim ke Medical Record Service
3. **Medical Record Service** simpan data pasien ke MySQL, dokter tambah diagnosis
4. **Medical Record Service** publish `PrescriptionCreated` dengan XML
5. **Integration Service** consume, transform XML → JSON, kirim ke Pharmacy Service
6. **Pharmacy Service** simpan resep, kurangi stok, publish `MedicineDispensed`
7. **Integration Service** consume, kirim ke Billing Service
8. **Billing Service** buat invoice, hitung biaya, publish `InvoiceCreated`
9. **Integration Service** log invoice

---

## Struktur Project

```
hospital-eai/
│
├── gateway/
│   └── nginx.conf                    # Nginx API Gateway
│
├── registration-service/             # Registration Service (PostgreSQL)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI endpoints
│   │   ├── database.py               # SQLAlchemy connection
│   │   ├── models.py                 # Patient model
│   │   ├── schemas.py                # Pydantic schemas
│   │   └── producer.py               # RabbitMQ producer
│   ├── Dockerfile
│   └── requirements.txt
│
├── medical-record-service/           # Medical Record Service (MySQL)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI endpoints
│   │   ├── database.py               # SQLAlchemy connection
│   │   ├── models.py                 # MedicalRecord model
│   │   ├── schemas.py                # Pydantic schemas
│   │   └── producer.py               # RabbitMQ producer
│   ├── Dockerfile
│   └── requirements.txt
│
├── pharmacy-service/                 # Pharmacy Service (MongoDB)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI endpoints
│   │   ├── database.py               # MongoDB connection
│   │   ├── schemas.py                # Pydantic schemas
│   │   └── producer.py               # RabbitMQ producer
│   ├── Dockerfile
│   └── requirements.txt
│
├── billing-service/                  # Billing Service (PostgreSQL)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI endpoints
│   │   ├── database.py               # SQLAlchemy connection
│   │   ├── models.py                 # Invoice model
│   │   ├── schemas.py                # Pydantic schemas
│   │   └── producer.py               # RabbitMQ producer
│   ├── Dockerfile
│   └── requirements.txt
│
├── integration-service/              # Integration Service (RabbitMQ Consumer)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app + startup
│   │   ├── consumer.py               # RabbitMQ consumer (all queues)
│   │   ├── translator.py             # JSON ↔ XML transformation
│   │   ├── router.py                 # Content-Based Router
│   │   └── producer.py               # DLQ Producer
│   ├── Dockerfile
│   └── requirements.txt
│
├── k8s/                              # Kubernetes manifests (bonus)
│   ├── postgres-registration-deployment.yaml
│   ├── postgres-billing-deployment.yaml
│   ├── mysql-medical-record-deployment.yaml
│   ├── mongodb-pharmacy-deployment.yaml
│   ├── rabbitmq-deployment.yaml
│   └── services.yaml
│
├── docker-compose.yml                # Docker Compose (semua service)
├── .env                              # Environment variables
└── README.md                         # Dokumentasi
```

---

## Fitur Bonus

### Dead Letter Queue (DLQ)
Setiap queue memiliki DLQ (`dlq_<queue_name>`) untuk menyimpan pesan yang gagal diproses.

### Retry Mechanism
Setiap service memiliki retry mechanism (3-5 attempts) dengan exponential backoff saat mengirim pesan ke RabbitMQ atau HTTP request ke service lain.

### Logging
Semua service menggunakan Python logging dengan format terstruktur dan tracing ID untuk observability.

### Message Tracing
Setiap event memiliki `tracing_id` unik yang ditambahkan ke dalam log untuk melacak alur pesan dari awal hingga akhir.

### Health Check
Setiap service memiliki endpoint `/health` yang mengembalikan status service.

### Kubernetes Deployment Manifest
Tersedia di folder `k8s/` untuk deployment ke Kubernetes cluster.

### Centralized Error Handling
Setiap service memiliki global exception handler yang menangani error dan mengembalikan response JSON yang konsisten.

### Observability
Integration Service menyediakan endpoint `/patterns` dan `/queues` untuk memonitor konfigurasi sistem.

---

## Swagger Documentation

Setiap service memiliki dokumentasi Swagger otomatis:

| Service | Swagger UI | Redoc |
|---------|-----------|-------|
| Registration | http://localhost:8001/docs | http://localhost:8001/redoc |
| Medical Record | http://localhost:8002/docs | http://localhost:8002/redoc |
| Pharmacy | http://localhost:8003/docs | http://localhost:8003/redoc |
| Billing | http://localhost:8004/docs | http://localhost:8004/redoc |
| Integration | http://localhost:8005/docs | http://localhost:8005/redoc |

---

## Prinsip Arsitektur

- **Loose Coupling**: Service berkomunikasi via message broker, tidak saling bergantung langsung
- **Scalability**: Setiap service bisa di-scale secara independen
- **Maintainability**: Source code terpisah per service, database sendiri
- **Enterprise Integration Patterns**: Implementasi 6 EIP patterns
- **Microservices Architecture**: Setiap service memiliki REST API, database, dan Dockerfile sendiri
- **Containerization Best Practices**: Docker multi-stage, environment variables, health check
