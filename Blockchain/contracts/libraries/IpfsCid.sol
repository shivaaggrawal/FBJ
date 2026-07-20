// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/// @notice Lightweight format validation for the CID forms accepted by FBJ.
/// @dev This validates encoding shape only. Evidence integrity is guaranteed by its on-chain Keccak hash.
library IpfsCid {
    function isValid(string calldata cid) internal pure returns (bool) {
        bytes calldata rawCid = bytes(cid);

        if (_isCidV0(rawCid)) return true;
        return _isCidV1(rawCid);
    }

    function _isCidV0(bytes calldata rawCid) private pure returns (bool) {
        if (rawCid.length != 46 || rawCid[0] != "Q" || rawCid[1] != "m") return false;

        for (uint256 i = 2; i < rawCid.length; ++i) {
            if (!_isBase58(rawCid[i])) return false;
        }
        return true;
    }

    function _isCidV1(bytes calldata rawCid) private pure returns (bool) {
        if (
            rawCid.length < 5 || rawCid.length > 128 || rawCid[0] != "b" || rawCid[1] != "a"
                || rawCid[2] != "f" || rawCid[3] != "y"
        ) return false;

        for (uint256 i = 4; i < rawCid.length; ++i) {
            if (!_isBase32Lower(rawCid[i])) return false;
        }
        return true;
    }

    function _isBase58(bytes1 character) private pure returns (bool) {
        return (character >= "1" && character <= "9") || (character >= "A" && character <= "H")
            || (character >= "J" && character <= "N") || (character >= "P" && character <= "Z")
            || (character >= "a" && character <= "k") || (character >= "m" && character <= "z");
    }

    function _isBase32Lower(bytes1 character) private pure returns (bool) {
        return (character >= "a" && character <= "z") || (character >= "2" && character <= "7");
    }
}
