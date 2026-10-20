import os
import re
import io
import uuid
import hmac
import hashlib
from datetime import datetime, date
import streamlit as st
import pandas as pd
import fitz
import bcrypt
from supabase import create_client

st.set_page_config(page_title="Fstep Social | Google Ads Raporları", page_icon="📊", layout="wide")
st.markdown("<style>.block-container{padding-top:1.7rem}div[data-testid='stMetric']{border:1px solid #ddd;border-radius:12px;padding:14px}</style>",unsafe_allow_html=True)

def conf(key):
    try: return st.secrets[key]
    except Exception: return os.getenv(key,"")

@st.cache_resource
def db():
    url, key = conf("SUPABASE_URL"), conf("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key: return None
    return create_client(url,key)

def login():
    if st.session_state.get("authenticated"): return True
    st.title("🔐 Fstep Social")
    st.caption("Google Ads günlük rapor arşivi ve performans analizi")
    username=st.text_input("Kullanıcı adı")
    password=st.text_input("Şifre",type="password")
    if st.button("Giriş yap",type="primary"):
        valid_user=hmac.compare_digest(username,conf("ADMIN_USERNAME"))
        saved=conf("ADMIN_PASSWORD_HASH")
        try: valid_password=bcrypt.checkpw(password.encode(),saved.encode())
        except (ValueError,TypeError): valid_password=False
        if valid_user and valid_password:
            st.session_state.authenticated=True
            st.rerun()
        else: st.error("Kullanıcı adı veya şifre hatalı.")
    return False

def parse_number(s):
    if s is None:return None
    s=str(s).replace("£","").replace("%","").replace(" ","").strip()
    if "," in s and "." in s:
        s=s.replace(".","").replace(",",".") if s.rfind(",")>s.rfind(".") else s.replace(",","")
    elif "," in s: s=s.replace(",",".")
    try:return float(s)
    except: return None

def extract_metrics(text):
    # Raporun ilk iki sayfasındaki toplam değerleri hedefler; sonuçlar yükleme öncesi düzenlenebilir.
    patterns={
      "spend":[r"TOPLAM HARCAMA\s*£?\s*([\d.,]+)",r"Harcama[^\n]{0,25}£\s*([\d.,]+)"],
      "impressions":[r"GÖSTERİM\s+TIKLAMA[^\n]*\n[^\n]*\n\s*([\d.,]+)",r"reklamlar\s+([\d.,]+)\s+kez gösterildi"],
      "clicks":[r"reklamlar\s+[\d.,]+\s+kez gösterildi,\s*([\d.,]+)\s+kişi tıkladı"],
      "conversions":[r"GELEN MÜŞTERİ TALEBİ\s+TALEP BAŞI MALİYET[^\n]*\n[^\n]*\n\s*£[\d.,]+\s+([\d.,]+)",r"([\d.,]+)\s+müşteri talebi\s*\(telefon araması\)\s+geldi"],
      "cpa":[r"TALEP BAŞI MALİYET[^\n]*\n[^\n]*\n\s*£[\d.,]+\s+[\d.,]+\s+£([\d.,]+)"],
      "ctr":[r"TIKLAMA ORANI\s+TIKLAMA BAŞI ÜCRET[^\n]*\n[^\n]*\n\s*[\d.,]+\s+[\d.,]+\s+%([\d.,]+)"],
      "cpc":[r"TIKLAMA BAŞI ÜCRET[^\n]*\n[^\n]*\n\s*[\d.,]+\s+[\d.,]+\s+%[\d.,]+\s+£([\d.,]+)"]
    }
    out={}
    for key, exprs in patterns.items():
        out[key]=None
        for pat in exprs:
            m=re.search(pat,text,re.IGNORECASE)
            if m:
                out[key]=parse_number(m.group(1))
                break
    if out["spend"] is not None and out["conversions"] and out["cpa"] is None:
        out["cpa"]=round(out["spend"]/out["conversions"],2)
    if out["impressions"] and out["clicks"] and out["ctr"] is None:
        out["ctr"]=round(out["clicks"] / out["impressions"] * 100,2)
    if out["spend"] is not None and out["clicks"] and out["cpc"] is None:
        out["cpc"]=round(out["spend"]/out["clicks"],2)
    return out

def pdf_text(raw):
    doc=fitz.open(stream=raw,filetype="pdf")
    if len(doc)>60: raise ValueError("PDF en fazla 60 sayfa olabilir.")
    return "\n".join(page.get_text(sort=True) for page in doc)

def fmt(value, suffix=""):
    return "—" if value is None else f"{value:,.2f}{suffix}"

if not login():st.stop()
client=db()
with st.sidebar:
    st.header("📊 Fstep Social")
    page=st.radio("Menü",["Genel Bakış","PDF Yükle","Rapor Arşivi","Firmalar"])
    if st.button("Çıkış yap"):
        st.session_state.authenticated=False
        st.rerun()
if client is None:
    st.error("Supabase bağlantısı yapılandırılmamış. Streamlit Secrets bölümüne SUPABASE_URL ve SUPABASE_SERVICE_ROLE_KEY girin.")
    st.stop()
try:
    firms=client.table("firms").select("id,name,website,currency").order("name").execute().data or []
except Exception as exc:
    st.error("Veritabanı tablolarına ulaşılamadı. Önce schema.sql dosyasını Supabase SQL Editor'de çalıştırın.")
    st.stop()
firm_names={f["name"]:f for f in firms}
st.title({"Genel Bakış":"📈 Genel Bakış","PDF Yükle":"📤 PDF Rapor Yükle","Rapor Arşivi":"🗂️ Rapor Arşivi","Firmalar":"🏢 Firmalar"}[page])
if page=="Firmalar":
    with st.form("new_firm"):
        name=st.text_input("Firma adı")
        website=st.text_input("Web sitesi")
        currency=st.selectbox("Para birimi",["GBP","TRY","USD","EUR"])
        save=st.form_submit_button("Firma ekle",type="primary")
    if save:
        if not name.strip():st.warning("Firma adı zorunlu.")
        else:
            try:
                client.table("firms").insert({"name":name.strip(),"website":website.strip(),"currency":currency}).execute()
                st.success("Firma eklendi.");st.rerun()
            except Exception as exc:
                msg=str(exc)
                if "duplicate key" in msg or "23505" in msg:
                    st.error("Bu firma adı zaten kayıtlı. Farklı bir isim kullanın.")
                else:
                    st.error("Firma kaydedilemedi. Supabase hatası: " + msg[:900])
    if firms:st.dataframe(pd.DataFrame(firms)[["name","website","currency"]],hide_index=True,use_container_width=True)
elif page=="PDF Yükle":
    if not firms:st.info("Önce Firmalar bölümünden firma oluşturun.");st.stop()
    chosen=st.selectbox("Firma",list(firm_names))
    report_date=st.date_input("Rapor tarihi",value=date.today(),max_value=date.today())
    file=st.file_uploader("PDF raporu seç",type=["pdf"])
    if file:
        raw=file.getvalue()
        if len(raw)>15*1024*1024:st.error("Dosya en fazla 15 MB olabilir.");st.stop()
        try: extracted=pdf_text(raw)
        except Exception:st.error("PDF okunamadı.");st.stop()
        metrics=extract_metrics(extracted)
        st.info("Otomatik okunan sayıları kontrol edip gerekirse düzeltin. Tarama PDF'ler için metin çıkarımı desteklenmeyebilir.")
        with st.form("upload_form"):
            c1,c2,c3=st.columns(3)
            with c1:
                spend=st.number_input("Harcama",min_value=0.0,value=float(metrics["spend"] or 0),step=1.0)
                imp=st.number_input("Gösterim",min_value=0,value=int(metrics["impressions"] or 0))
            with c2:
                clicks=st.number_input("Tıklama",min_value=0,value=int(metrics["clicks"] or 0))
                conv=st.number_input("Dönüşüm / talep",min_value=0,value=int(metrics["conversions"] or 0))
            with c3:
                cpc=st.number_input("Tıklama başı maliyet",min_value=0.0,value=float(metrics["cpc"] or 0))
                ctr=st.number_input("CTR (%)",min_value=0.0,value=float(metrics["ctr"] or 0))
            save=st.form_submit_button("PDF'yi arşive kaydet",type="primary")
        if save:
            firm=firm_names[chosen]
            path=f'{firm["id"]}/{report_date.isoformat()}/{uuid.uuid4()}.pdf'
            try:
                client.storage.from_("ads-reports").upload(path,raw,{"content-type":"application/pdf"})
                try:
                    client.table("reports").insert({
                      "firm_id":firm["id"],"report_date":report_date.isoformat(),"file_path":path,
                      "file_name":file.name[:240],"file_hash":hashlib.sha256(raw).hexdigest(),
                      "spend":spend,"impressions":imp,"clicks":clicks,"conversions":conv,
                      "cpc":cpc,"ctr":ctr,"cpa":round(spend/conv,2) if conv else None,
                      "extracted_text":extracted[:150000]
                    }).execute()
                except Exception:
                    client.storage.from_("ads-reports").remove([path])
                    raise
                st.success("Rapor özel bulut arşivine kaydedildi.")
            except Exception as exc:
                st.error("Kaydetme başarısız. Aynı tarihli rapor veya veritabanı ayarlarını kontrol edin.")
elif page in ("Genel Bakış","Rapor Arşivi"):
    if not firms:st.info("Başlamak için Firmalar bölümüne bir firma ekleyin.");st.stop()
    chosen=st.selectbox("Firma",["Tüm Firmalar"]+list(firm_names))
    query=client.table("reports").select("id,firm_id,report_date,file_path,file_name,spend,impressions,clicks,conversions,cpc,ctr,cpa,extracted_text").order("report_date",desc=True).limit(1000)
    if chosen!="Tüm Firmalar":query=query.eq("firm_id",firm_names[chosen]["id"])
    reports=query.execute().data or []
    for r in reports:r["firma"]=next((f["name"] for f in firms if f["id"]==r["firm_id"]),"—")
    if not reports:st.info("Henüz rapor yüklenmedi.");st.stop()
    df=pd.DataFrame(reports)
    currencies={f["currency"] for f in firms if chosen=="Tüm Firmalar" or f["name"]==chosen}
    if page=="Genel Bakış":
        if len(currencies)>1:
            st.warning("Farklı para birimleri var; toplam harcama yalnızca tek para birimi seçildiğinde hesaplanır.")
        a,b,c,d=st.columns(4)
        a.metric("Rapor sayısı",len(df))
        b.metric("Toplam harcama",fmt(df.spend.fillna(0).sum())+" "+next(iter(currencies)) if len(currencies)==1 else "—")
        c.metric("Tıklama",int(df.clicks.fillna(0).sum()))
        d.metric("Dönüşüm",int(df.conversions.fillna(0).sum()))
        byday=df.groupby("report_date",as_index=False)[["spend","clicks","conversions"]].sum().sort_values("report_date")
        st.subheader("Günlük gelişim")
        st.line_chart(byday.set_index("report_date")[["clicks","conversions"]])
        if len(currencies)==1:st.bar_chart(byday.set_index("report_date")[["spend"]])
        if chosen!="Tüm Firmalar" and len(df)>=2:
            rows=df.sort_values("report_date",ascending=False).iloc[:2]
            latest,previous=rows.iloc[0],rows.iloc[1]
            st.subheader("Son iki rapor karşılaştırması")
            for label,key in [("Harcama","spend"),("Tıklama","clicks"),("Dönüşüm","conversions"),("Talep başı maliyet","cpa")]:
                st.write(f'**{label}:** {fmt(latest[key])} (önceki: {fmt(previous[key])})')
        st.info("Dönüşüm sayısı, raporda ölçülen reklam aksiyonlarıdır; kesinleşmiş satış sayısı değildir.")
    else:
        import base64
        st.subheader("Tarih filtresi")
        days=pd.to_datetime(df["report_date"]).dt.date
        period=st.date_input("Başlangıç / bitiş",(days.min(),days.max()),min_value=days.min(),max_value=days.max())
        if isinstance(period,(tuple,list)) and len(period)==2:
            filtered=df[(days>=period[0])&(days<=period[1])].copy()
        elif isinstance(period,(tuple,list)) and len(period)==1:
            filtered=df[days==period[0]].copy()
        else:
            filtered=df[days==period].copy()
        if filtered.empty:
            st.info("Seçili tarihlerde rapor yok.")
            st.stop()
        st.subheader("Firma harcamaları")
        curr={f["name"]:f["currency"] for f in firms}
        symbols={"GBP":"£","TRY":"₺","USD":"$","EUR":"€"}
        totals=filtered.groupby("firma")["spend"].sum()
        for name,amount in totals.items():
            st.metric(name,f'{symbols.get(curr.get(name),"")}{amount:,.2f}')
        codes={curr.get(name) for name in totals.index}
        if len(codes)==1:
            st.metric("GENEL TOPLAM",f'{symbols.get(next(iter(codes)),"")}{filtered["spend"].sum():,.2f}')
        else:
            st.warning("Farklı para birimleri ayrı hesaplanır.")
            for code in sorted(codes):
                names=[name for name in totals.index if curr.get(name)==code]
                st.metric("Toplam "+code,f'{totals.loc[names].sum():,.2f} {code}')
        st.caption("Firma filtresi üstteki Firma seçiminden yapılır.")
        st.subheader("PDF Arşivi")
        for _,item in filtered.sort_values("report_date",ascending=False).iterrows():
            a,b,c=st.columns([2,3,1])
            a.write(str(item["report_date"])+" · "+item["firma"])
            b.write(item["file_name"])
            if c.button("👁",key="eye_"+item["id"],help="PDF ön izle"):
                st.session_state["pdf_preview"]=item["id"]
            if st.session_state.get("pdf_preview")==item["id"]:
                try:
                    data=client.storage.from_("ads-reports").download(item["file_path"])
                    st.download_button("PDF indir",data=data,file_name=item["file_name"],mime="application/pdf",key="download_"+item["id"])
                    with fitz.open(stream=data,filetype="pdf") as document:
                        st.caption(f"PDF önizleme · {len(document)} sayfa")
                        page_number=st.number_input("Sayfa",min_value=1,max_value=len(document),value=1,step=1,key="page_"+item["id"])
                        pix=document[page_number-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
                        st.image(pix.tobytes("png"),caption=f"Sayfa {page_number} / {len(document)}",use_container_width=True)
                    if st.button("Önizlemeyi kapat",key="close_"+item["id"]):
                        st.session_state.pop("pdf_preview",None)
                        st.rerun()
                except Exception as exc:
                    st.error("PDF açılamadı: "+str(exc)[:300])
            st.divider()
