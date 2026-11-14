using Microsoft.Extensions.Options;
using Shop.Application.Settings;

namespace Shop.Application.Jobs;

/// <summary>First background job: queues one message per configured route.</summary>
public sealed class ExpansionJob(IOptionsMonitor<OrderRoutesSettings> routes)
{
    public int Expand() => routes.CurrentValue.Routes.Count;
}

/// <summary>Second background job: delivers queued messages to each route's client.</summary>
public sealed class DeliveryJob(IOptionsMonitor<OrderRoutesSettings> routes)
{
    public IEnumerable<string> Clients() => routes.CurrentValue.Routes.Select(r => r.Client);
}
