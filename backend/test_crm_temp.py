import pandas as pd
from app.services.crm_service import get_crm_service

crm = get_crm_service()
df = crm.get_equipos_dataframe(["JK1142005099"])

if df is not None and not df.empty:
    print("✅ Columnas del CRM:")
    print(df.columns.tolist())
    print("\n📄 Primer registro:")
    print(df.iloc[0].to_dict())
else:
    print("❌ Sin datos del CRM")