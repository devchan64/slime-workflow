"""관리도구 공통 접이식 로그 뷰어 스크립트."""
MANAGEMENT_LOG_VIEWER_SCRIPT = r"""(() => {
  const scrollToEnd = element => requestAnimationFrame(() => { element.scrollTop = element.scrollHeight; });
  window.ManagementLogViewer = {
    attach(details, output) {
      details.addEventListener('toggle', () => { if (details.open) scrollToEnd(output); });
      return {
        update(text) {
          output.textContent = text || '로그 대기';
          if (details.open) scrollToEnd(output);
        },
        scrollToEnd: () => scrollToEnd(output),
      };
    },
  };
})();"""
