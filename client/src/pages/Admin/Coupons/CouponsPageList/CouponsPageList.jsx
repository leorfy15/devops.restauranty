import React, { useState, useEffect } from "react";
import axios from "axios";
import Coupon from "../../../../components/Coupon/Coupon";
import { Link } from "react-router-dom";
import { FaTrashCan } from "react-icons/fa6"
import { FaPen } from "react-icons/fa6"

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function CouponPageList() {
    const [coupons, setCoupons] = useState([]);

    useEffect(() => {
        axios.get(`${url}/api/discounts/coupons`).then((response) => {
            setCoupons(response.data);
            console.log(response.data)
        });
    }, []);

    function deleteItem(id) {
        axios.delete(`${url}/api/discounts/coupons/${id}`).then((response) => {
            setCoupons((prevItems) => prevItems.filter((coupon) => coupon._id !== id));
        });
    }

    return (
        <div>
            <h1>Coupons</h1>
            <div className="page-container">
                <table className="centered-table">
                    <thead>
                        <tr>
                            <th>Code Coupon</th>
                            <th className="w-60">Initial Date</th>
                            <th className="w-60">Expiry Date</th>
                            <th colSpan="2">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {coupons.map((coupon) => (
                            <tr key={coupon._id}>
                                <td><Coupon coupon={coupon} /></td>
                                <td>{coupon.start}</td>
                                <td>{coupon.end}</td>
                                <td><Link to={`/editCoupon/${coupon._id}`}><button className="button-acoes-edit"><FaPen /></button></Link></td>
                                <td><button className="button-acoes-delete" onClick={() => deleteItem(coupon._id)}><FaTrashCan /></button></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div >
    );
}

export default CouponPageList;
