import "websocket-polyfill";
import { webln } from "@getalby/sdk";

class Provider {
  constructor(loadNWCUrl) {
    this.nwc = new webln.NWC({ nostrWalletConnectUrl: loadNWCUrl });
    this.enabled = false;
  }

  async enable() {
    if (!this.enabled) {
      await this.nwc.enable();
      this.enabled = true;
    }
  }

  async getBalance() {
    await this.enable();
    return await this.nwc.getBalance();
  }

  async makeInvoice(payload) {
    await this.enable();
    return await this.nwc.makeInvoice({
      amount: payload.amount,
      defaultMemo: payload.memo,
    });
  }

  async sendPayment(invoice) {
    await this.enable();
    return await this.nwc.sendPayment(invoice);
  }
}

export default Provider;
