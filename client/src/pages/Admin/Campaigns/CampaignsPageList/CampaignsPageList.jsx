import React, { useState, useEffect } from "react";
import axios from "axios";
import Campaign from "../../../../components/Campaign/Campaign";
import { Link } from "react-router-dom";
import { FaTrashCan } from "react-icons/fa6"
import { FaPen } from "react-icons/fa6"

const url = process.env.REACT_APP_SERVER_URL || window.location.origin;

function CampaignsPageList() {
    const [campaigns, setCampaigns] = useState([]);

    useEffect(() => {
        axios.get(`${url}/api/discounts/campaign`).then((response) => {
            setCampaigns(response.data);
            console.log(response.data)
        });
    }, []);

    function deleteItem(id) {
        axios.delete(`${url}/api/discounts/campaign/${id}`).then((response) => {
            setCampaigns((prevItems) => prevItems.filter((campaign) => campaign._id !== id));
        });
    }

    return (
        <div>
            <h1>Campaigns</h1>
            <div className="page-container">
                <table className="centered-table">
                    <thead>
                        <tr>
                            <th>Campaign</th>
                            <th className="w-60">Initial Date</th>
                            <th className="w-60">Expiry Date</th>
                            <th colSpan="2">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {campaigns.map((campaign) => (
                            <tr key={campaign._id}>
                                <td><Campaign campaign={campaign} /></td>
                                <td>{campaign.start}</td>
                                <td>{campaign.end}</td>
                                <td><Link to={`/EditCampaign/${campaign._id}`}><button className="button-acoes-edit"><FaPen /></button></Link></td>
                                <td><button className="button-acoes-delete" onClick={() => deleteItem(campaign._id)}><FaTrashCan /></button></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div >
    );
}

export default CampaignsPageList;
