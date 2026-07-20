import { isAddress, isHexString } from "ethers";

export function scriptArgs(expectedCount: number, usage: string): string[] {
  const args = process.argv.slice(2).filter((arg) => arg !== "--");
  if (args.length !== expectedCount) throw new Error(`Usage: ${usage}`);
  return args;
}

export function requireAddress(value: string, label: string): string {
  if (!isAddress(value)) throw new Error(`${label} must be a valid EVM address`);
  return value;
}

export function requireBountyId(value: string): string {
  if (!isHexString(value, 32) || value === "0x" + "00".repeat(32)) {
    throw new Error("bountyId must be a non-zero bytes32 hex value");
  }
  return value;
}

export function requirePositiveInteger(value: string, label: string): bigint {
  if (!/^[1-9][0-9]*$/.test(value)) throw new Error(`${label} must be a positive integer`);
  return BigInt(value);
}
