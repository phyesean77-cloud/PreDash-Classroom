"""Broker selection UI. Broker-specific account adapters are enabled only after verified API support."""
import streamlit as st


BROKERS = {
    "KB증권": {
        "status": "API 연동 준비 중",
        "note": "공식 Open API 앱 키와 잔고 조회 규격을 확인한 뒤 연결 기능을 활성화합니다.",
        "url": "https://openapi.kbsec.com/",
    },
    "미래에셋증권": {
        "status": "공식 API 확인 필요",
        "note": "개인 계좌 조회에 사용할 공식 API 및 접근 권한을 확인한 뒤 연결 기능을 활성화합니다.",
        "url": "https://securities.miraeasset.com/",
    },
}


def account_settings(mode=None):
    """Compatibility shape for existing dashboard code; no unsupported broker is treated as connected."""
    selected = mode or st.session_state.get("selected_broker_mode", "real")
    return dict(mode=selected, key="", secret="", cano="", product="",
                broker=st.session_state.get("selected_broker", "KB증권"))


def connection_form():
    st.subheader("내 증권사 계좌 연결")
    st.caption("사용할 증권사를 선택하세요. 인증 및 잔고 조회 API 검증이 끝난 증권사만 실제 연결할 수 있습니다.")
    names = list(BROKERS)
    current = st.session_state.get("selected_broker", "KB증권")
    selected = st.radio("증권사 선택", names, horizontal=True,
                        index=names.index(current) if current in names else 0,
                        key="selected_broker")
    info = BROKERS[selected]
    st.markdown(f"**연동 상태 · {info['status']}**")
    st.write(info["note"])
    st.link_button(f"{selected} 공식 사이트 / API 안내", info["url"], use_container_width=True)
    if st.session_state.get("classroom_credentials"):
        st.session_state.pop("classroom_credentials", None)
    st.info("현재는 한국투자증권 계좌 연결을 사용하지 않습니다. KB증권·미래에셋증권의 실제 API 연동은 검증 후 활성화됩니다.")
