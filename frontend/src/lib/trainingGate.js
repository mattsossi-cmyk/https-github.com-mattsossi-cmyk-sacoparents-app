export const trainingRedirect = (e, navigate) => {
  if (e?.response?.status === 428 && e.response.data?.detail?.code === "training_required") {
    sessionStorage.setItem("post-training-redirect", window.location.pathname);
    navigate("/professional-training", { replace: true });
    return true;
  }
  return false;
};
