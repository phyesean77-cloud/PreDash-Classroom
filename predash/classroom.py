"""Broker selection UI with session-only credential handling."""
import streamlit as st

from predash.brokers import KBOpenAPI, BrokerConnectionError


BROKERS = {
    "KB증권": {
        "status": "인증 확인 가능 · 잔고 API 검증 중",
        "note": "공식 Open API appKey/appSecret으로 토큰 발급을 확인합니다. 잔고·체결 조회는 요청/응답 규격 검증 후 활성화됩니다.",
        "url": "https://openapi.kbsec.com/",
    },
    "미래에셋증권": {
        "status": "공식 API 확인 필요",
        "note": "개인 계좌 조회에 사용할 공식 API 규격과 이용 권한이 확인되지 않아 아직 연결할 수 없습니다.",
        "url": "https://securities.miraeasset.com/",
    },
}


def account_settings(mode=None):
    """Compatibility shape for legacy dashboard code; never provides KIS credentials."""
    selected = mode or st.session_state.get("selected_broker_mode", "real")
    return dict(
        mode=selected, key="", secret="", cano="", product="",
        broker=st.session_state.get("selected_broker", "KB증권"),
    )


def connection_form():
    st.subheader("내 증권사 계좌 연결")
    st.caption("한국투자증권 연결은 사용하지 않습니다. 인증 키는 현재 브라우저 세션에서만 보관하며 GitHub나 디스크에 저장하지 않습니다.")

    names = list(BROKERS)
    current = st.session_state.get("selected_broker", "KB증권")
    selected = st.radio(
        "증권사 선택", names, horizontal=True,
        index=names.index(current) if current in names else 0,
        key="selected_broker",
    )

    # Never carry credentials or an auth result across brokers.
    previous = st.session_state.get("_broker_form_for")
    if previous != selected:
        for key in ("kb_app_key", "kb_app_secret", "kb_auth_ok", "kb_auth_error", "kb_access_token"):
            st.session_state.pop(key, None)
        st.session_state["_broker_form_for"] = selected

    info = BROKERS[selected]
    st.markdown(f"**연동 상태 · {info['status']}**")
    st.write(info["note"])
    st.link_button(f"{selected} 공식 사이트 / API 안내", info["url"], use_container_width=True)

    if selected == "KB증권":
        with st.form("kb_openapi_auth_form", clear_on_submit=False):
            app_key = st.text_input(
                "KB증권 appKey", type="password",
                value=st.session_state.get("kb_app_key", ""),
                help="KB증권 Open API 포털에서 발급한 appKey를 입력하세요.",
            )
            app_secret = st.text_input(
                "KB증권 appSecret", type="password",
                value=st.session_state.get("kb_app_secret", ""),
                help="화면에 표시하거나 GitHub에 올리지 마세요.",
            )
            submitted = st.form_submit_button("KB증권 API 인증 확인", type="primary", use_container_width=True)

        if submitted:
            st.session_state.pop("kb_auth_ok", None)
            st.session_state.pop("kb_access_token", None)
            st.session_state.pop("kb_auth_error", None)
            try:
                client = KBOpenAPI(app_key, app_secret)
                client.authorize()
                # Keep credentials/token in this Streamlit session only; never render the token.
                st.session_state["kb_app_key"] = app_key.strip()
                st.session_state["kb_app_secret"] = app_secret.strip()
                st.session_state["kb_access_token"] = client.access_token
                st.session_state["kb_auth_ok"] = True
            except BrokerConnectionError as exc:
                st.session_state["kb_auth_error"] = str(exc)

        if st.session_state.get("kb_auth_ok"):
            st.success("KB증권 API 인증 성공 · 토큰 발급 확인")
            st.warning("잔고·체결 조회는 아직 연결되지 않았습니다. 공식 API 명세의 계좌 조회 규격 검증 전에는 실제 자산 데이터를 표시하지 않습니다.")
        elif st.session_state.get("kb_auth_error"):
            st.error(st.session_state["kb_auth_error"])

        if st.button("KB증권 세션 인증정보 지우기", use_container_width=True):
            for key in ("kb_app_key", "kb_app_secret", "kb_auth_ok", "kb_auth_error", "kb_access_token"):
                st.session_state.pop(key, None)
            st.rerun()
    else:
        st.info("미래에셋증권은 공식 개인 계좌 조회 API의 규격과 이용 권한이 확인되기 전까지 인증정보를 받거나 연결 완료로 표시하지 않습니다.")

    st.caption("보안 안내: appKey/appSecret을 GitHub 코드, 커밋, 공개 게시판에 입력하지 마세요.")
