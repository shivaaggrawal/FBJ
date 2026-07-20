// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";

contract FeeOnTransferToken is ERC20 {
    uint16 public constant FEE_BPS = 100;
    address public immutable feeCollector;

    constructor(address initialFeeCollector) ERC20("Fee Token", "FEE") {
        feeCollector = initialFeeCollector;
    }

    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    function _update(address from, address to, uint256 value) internal override {
        if (from == address(0) || to == address(0)) {
            super._update(from, to, value);
            return;
        }

        uint256 fee = (value * FEE_BPS) / 10_000;
        super._update(from, feeCollector, fee);
        super._update(from, to, value - fee);
    }
}
